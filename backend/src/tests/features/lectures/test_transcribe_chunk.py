from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from celery.exceptions import MaxRetriesExceededError
from openai import AuthenticationError, InternalServerError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.celery import celery_app
from src.features.lectures import tasks
from src.features.lectures.ai.transcription import is_permanent_transcription_error
from src.features.lectures.models import (
    LectureAudioChunkModel,
    LectureAudioModel,
    LectureModel,
    LectureStatus,
)
from src.features.lectures.services import import_pipeline


def _openai_error(cls, code: str | None, status_code: int):
    request = httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")
    body = {"error": {"code": code, "message": "boom"}} if code else None
    return cls(
        "boom",
        response=httpx.Response(status_code, request=request),
        body=body,
    )


class TestErrorClassification:
    def test_exhausted_credit_is_permanent(self):
        assert is_permanent_transcription_error(
            _openai_error(RateLimitError, "insufficient_quota", 429)
        )

    def test_throughput_rate_limit_is_transient(self):
        assert not is_permanent_transcription_error(
            _openai_error(RateLimitError, "rate_limit_exceeded", 429)
        )

    def test_a_rate_limit_without_a_code_is_transient(self):
        assert not is_permanent_transcription_error(_openai_error(RateLimitError, None, 429))

    def test_bad_credentials_are_permanent(self):
        assert is_permanent_transcription_error(
            _openai_error(AuthenticationError, "invalid_api_key", 401)
        )

    def test_a_server_error_is_transient(self):
        assert not is_permanent_transcription_error(
            _openai_error(InternalServerError, None, 500)
        )


@pytest_asyncio.fixture
async def chunk(db_session: AsyncSession, test_user: dict) -> LectureAudioChunkModel:
    lecture = LectureModel(
        user_id=test_user["id"], title="Aula importada", status=LectureStatus.PROCESSING
    )
    db_session.add(lecture)
    await db_session.flush()

    audio = LectureAudioModel(
        lecture_id=lecture.id,
        sequence=1,
        object_key=f"lectures/{lecture.id}/imports/01_aula.mp3",
        original_filename="aula.mp3",
        duration_seconds=600.0,
    )
    db_session.add(audio)
    await db_session.flush()

    model = LectureAudioChunkModel(
        audio_id=audio.id,
        sequence=0,
        object_key=f"lectures/{lecture.id}/chunks/{audio.id}/0000.ogg",
        start_seconds=0.0,
        duration_seconds=600.0,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest.fixture
def use_test_session(test_engine, monkeypatch):
    monkeypatch.setattr(
        import_pipeline,
        "AsyncSessionLocal",
        async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False),
    )


@pytest.fixture
def bucket(monkeypatch):
    class _Bucket:
        def download_to(self, key: str, path: Path) -> None:
            path.write_bytes(b"ogg")

    monkeypatch.setattr(import_pipeline, "get_bucket_service", lambda: _Bucket())


@pytest.fixture
def openai_calls(monkeypatch) -> list[Path]:
    calls: list[Path] = []

    async def fake(path: Path) -> str:
        calls.append(path)
        return "texto transcrito"

    monkeypatch.setattr(import_pipeline, "transcribe_chunk_path", fake)
    return calls


@pytest.mark.asyncio
class TestTranscribeChunk:
    async def test_writes_the_transcript_and_counts_the_attempt(
        self, db_session: AsyncSession, chunk, use_test_session, bucket, openai_calls
    ):
        await import_pipeline.transcribe_chunk(chunk.id)

        await db_session.refresh(chunk)
        assert chunk.transcript == "texto transcrito"
        assert chunk.attempts == 1
        assert chunk.last_error is None
        assert len(openai_calls) == 1

    async def test_a_chunk_already_transcribed_never_reaches_openai(
        self, db_session: AsyncSession, chunk, use_test_session, bucket, openai_calls
    ):
        chunk.transcript = "já estava pronto"
        await db_session.commit()

        await import_pipeline.transcribe_chunk(chunk.id)

        await db_session.refresh(chunk)
        assert openai_calls == []
        assert chunk.transcript == "já estava pronto"
        assert chunk.attempts == 0

    async def test_running_twice_bills_once(
        self, db_session: AsyncSession, chunk, use_test_session, bucket, openai_calls
    ):
        await import_pipeline.transcribe_chunk(chunk.id)
        await import_pipeline.transcribe_chunk(chunk.id)

        await db_session.refresh(chunk)
        assert len(openai_calls) == 1
        assert chunk.attempts == 1

    async def test_a_failure_records_the_reason_and_re_raises(
        self, db_session: AsyncSession, chunk, use_test_session, bucket, monkeypatch
    ):
        async def explode(path: Path) -> str:
            raise _openai_error(RateLimitError, "insufficient_quota", 429)

        monkeypatch.setattr(import_pipeline, "transcribe_chunk_path", explode)

        with pytest.raises(RateLimitError):
            await import_pipeline.transcribe_chunk(chunk.id)

        await db_session.refresh(chunk)
        assert chunk.transcript is None
        assert chunk.attempts == 1
        assert "RateLimitError" in (chunk.last_error or "")

    async def test_a_missing_chunk_is_a_no_op(self, use_test_session, bucket, openai_calls):
        await import_pipeline.transcribe_chunk(uuid4())
        assert openai_calls == []


class _FakeTask:
    def __init__(self, retries: int, retried: list) -> None:
        self.request = SimpleNamespace(retries=retries)
        self._retried = retried

    def retry(self, **kwargs):
        if self.request.retries >= tasks.MAX_RETRIES:
            raise MaxRetriesExceededError()
        self._retried.append(kwargs)
        raise Retried()


class Retried(Exception):
    pass


@pytest.mark.asyncio
class TestTranscribeChunkBody:
    """O corpo compartilhado pelos dois pools — prefork embrulha em run_async,
    o pool async o aguarda direto."""

    @pytest.fixture
    def harness(self, monkeypatch):
        retried: list[dict] = []
        failed: list[tuple] = []
        consolidated: list[str] = []

        async def fake_fail(chunk_id, reason):
            failed.append((chunk_id, reason))

        monkeypatch.setattr(import_pipeline, "fail_audio_of_chunk", fake_fail)
        monkeypatch.setattr(
            tasks.consolidate_audio_task, "delay", lambda audio_id: consolidated.append(audio_id)
        )

        async def run(error: BaseException | None, retries: int = 0, audio_id=None):
            async def fake(chunk_id):
                if error is not None:
                    raise error
                return audio_id

            monkeypatch.setattr(import_pipeline, "transcribe_chunk", fake)
            task = _FakeTask(retries, retried)
            return await tasks._run_transcribe_chunk(task, str(uuid4()))

        return SimpleNamespace(
            run=run, retried=retried, failed=failed, consolidated=consolidated
        )

    async def test_a_permanent_error_is_not_retried(self, harness):
        await harness.run(_openai_error(RateLimitError, "insufficient_quota", 429))
        assert harness.retried == []
        assert len(harness.failed) == 1

    async def test_a_transient_error_is_retried(self, harness):
        with pytest.raises(Retried):
            await harness.run(_openai_error(InternalServerError, None, 500))
        assert len(harness.retried) == 1
        assert harness.retried[0]["countdown"] == 10

    async def test_the_backoff_grows_with_each_attempt(self, harness):
        with pytest.raises(Retried):
            await harness.run(_openai_error(InternalServerError, None, 500), retries=2)
        assert harness.retried[0]["countdown"] == 40

    async def test_it_gives_up_after_the_last_retry(self, harness):
        await harness.run(
            _openai_error(InternalServerError, None, 500), retries=tasks.MAX_RETRIES
        )
        assert harness.retried == []
        assert len(harness.failed) == 1

    async def test_success_does_not_retry(self, harness):
        await harness.run(None)
        assert harness.retried == []
        assert harness.failed == []

    async def test_success_asks_the_audio_to_consolidate(self, harness):
        audio_id = uuid4()
        await harness.run(None, audio_id=audio_id)
        assert harness.consolidated == [str(audio_id)]


class TestPoolWiring:
    def test_each_stage_has_its_own_queue(self):
        routes = celery_app.conf.task_routes
        assert routes["transcribe_chunk_task"]["queue"] == "chunks"
        assert routes["generate_lecture_summary_task"]["queue"] == "summaries"
        assert routes["chunk_audio_task"]["queue"] == "audios"
