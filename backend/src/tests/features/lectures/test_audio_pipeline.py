from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.features.lectures.models import (
    LectureAudioChunkModel,
    LectureAudioModel,
    LectureAudioStatus,
    LectureModel,
    LectureSegmentModel,
    LectureStatus,
)
from src.features.lectures.services import import_pipeline


class _Bucket:
    def __init__(self) -> None:
        self.uploaded: list[str] = []
        self.deleted: list[str] = []

    def download_to(self, key: str, path: Path) -> None:
        Path(path).write_bytes(b"audio")

    def upload_stream(self, stream, name, *, length, content_type=None, folder=None, key=None):
        self.uploaded.append(key or name)

    def delete_many(self, keys: list[str]) -> None:
        self.deleted.extend(keys)


@pytest.fixture
def bucket(monkeypatch) -> _Bucket:
    fake = _Bucket()
    monkeypatch.setattr(import_pipeline, "get_bucket_service", lambda: fake)
    return fake


@pytest.fixture
def use_test_session(test_engine, monkeypatch):
    monkeypatch.setattr(
        import_pipeline,
        "AsyncSessionLocal",
        async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False),
    )


@pytest.fixture
def three_chunks(monkeypatch, tmp_path):
    async def fake_prepare(src_path, out_dir, duration_hint=None):
        paths = []
        for index in range(3):
            path = Path(out_dir) / f"parte_{index}.ogg"
            path.write_bytes(b"ogg")
            paths.append(path)
        return paths

    async def fake_probe(path: Path) -> float:
        return 200.0

    monkeypatch.setattr(import_pipeline, "prepare_audio_for_whisper", fake_prepare)
    monkeypatch.setattr(import_pipeline, "probe_duration_seconds", fake_probe)


@pytest_asyncio.fixture
async def audio(db_session: AsyncSession, test_user: dict) -> LectureAudioModel:
    lecture = LectureModel(
        user_id=test_user["id"], title="Aula importada", status=LectureStatus.PROCESSING
    )
    db_session.add(lecture)
    await db_session.flush()

    model = LectureAudioModel(
        lecture_id=lecture.id,
        sequence=1,
        object_key=f"lectures/{lecture.id}/imports/01_aula.mp3",
        original_filename="aula.mp3",
        duration_seconds=600.0,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


async def _chunks(db: AsyncSession, audio_id) -> list[LectureAudioChunkModel]:
    result = await db.execute(
        select(LectureAudioChunkModel)
        .where(LectureAudioChunkModel.audio_id == audio_id)
        .order_by(LectureAudioChunkModel.sequence)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
class TestChunkAudio:
    async def test_it_uploads_every_chunk_and_records_a_row_for_each(
        self, db_session: AsyncSession, audio, use_test_session, bucket, three_chunks
    ):
        chunk_ids = await import_pipeline.chunk_audio(audio.id)

        chunks = await _chunks(db_session, audio.id)
        await db_session.refresh(audio)

        assert len(chunk_ids) == 3
        assert [chunk.sequence for chunk in chunks] == [0, 1, 2]
        assert [chunk.start_seconds for chunk in chunks] == [0.0, 200.0, 400.0]
        assert all(chunk.duration_seconds == 200.0 for chunk in chunks)
        assert all(chunk.transcript is None for chunk in chunks)
        assert bucket.uploaded == [chunk.object_key for chunk in chunks]
        assert audio.status is LectureAudioStatus.TRANSCRIBING

    async def test_the_keys_are_deterministic(
        self, db_session: AsyncSession, audio, use_test_session, bucket, three_chunks
    ):
        await import_pipeline.chunk_audio(audio.id)
        chunks = await _chunks(db_session, audio.id)

        expected = f"lectures/{audio.lecture_id}/chunks/{audio.id}/0000.ogg"
        assert chunks[0].object_key == expected

    async def test_running_it_again_does_not_duplicate_or_lose_a_transcript(
        self, db_session: AsyncSession, audio, use_test_session, bucket, three_chunks
    ):
        await import_pipeline.chunk_audio(audio.id)

        chunks = await _chunks(db_session, audio.id)
        chunks[0].transcript = "primeira parte"
        audio.status = LectureAudioStatus.CHUNKING
        await db_session.commit()

        await import_pipeline.chunk_audio(audio.id)

        chunks = await _chunks(db_session, audio.id)
        assert len(chunks) == 3
        assert chunks[0].transcript == "primeira parte"

    async def test_an_audio_past_this_stage_is_left_alone(
        self, db_session: AsyncSession, audio, use_test_session, bucket, three_chunks
    ):
        audio.status = LectureAudioStatus.DONE
        await db_session.commit()

        assert await import_pipeline.chunk_audio(audio.id) == []
        assert await _chunks(db_session, audio.id) == []


@pytest_asyncio.fixture
async def transcribed(db_session: AsyncSession, audio) -> LectureAudioModel:
    for sequence, text in enumerate(["primeira", "segunda", "terceira"]):
        db_session.add(
            LectureAudioChunkModel(
                audio_id=audio.id,
                sequence=sequence,
                object_key=f"chunks/{audio.id}/{sequence:04d}.ogg",
                start_seconds=sequence * 200.0,
                duration_seconds=200.0,
                transcript=text,
            )
        )
    audio.status = LectureAudioStatus.TRANSCRIBING
    await db_session.commit()
    return audio


@pytest.mark.asyncio
class TestConsolidateAudio:
    async def test_it_joins_the_chunks_into_one_segment(
        self, db_session: AsyncSession, transcribed, use_test_session, bucket
    ):
        lecture_id = await import_pipeline.consolidate_audio(transcribed.id)

        result = await db_session.execute(
            select(LectureSegmentModel).where(LectureSegmentModel.lecture_id == lecture_id)
        )
        segments = list(result.scalars().all())

        assert len(segments) == 1
        assert segments[0].transcript == "primeira segunda terceira"
        assert segments[0].sequence == transcribed.sequence
        assert segments[0].offset_seconds == 0.0

    async def test_it_records_what_was_sent_before_dropping_the_chunks(
        self, db_session: AsyncSession, transcribed, use_test_session, bucket
    ):
        await import_pipeline.consolidate_audio(transcribed.id)

        await db_session.refresh(transcribed)
        assert transcribed.transcribed_seconds == 600.0
        assert transcribed.model
        assert transcribed.status is LectureAudioStatus.DONE

    async def test_success_deletes_the_chunks_and_the_original_audio(
        self, db_session: AsyncSession, transcribed, use_test_session, bucket
    ):
        chunk_keys = [chunk.object_key for chunk in await _chunks(db_session, transcribed.id)]

        await import_pipeline.consolidate_audio(transcribed.id)

        assert bucket.deleted == chunk_keys + [transcribed.object_key]
        assert await _chunks(db_session, transcribed.id) == []

    async def test_a_pending_chunk_blocks_consolidation(
        self, db_session: AsyncSession, transcribed, use_test_session, bucket
    ):
        chunks = await _chunks(db_session, transcribed.id)
        chunks[1].transcript = None
        await db_session.commit()

        assert await import_pipeline.consolidate_audio(transcribed.id) is None

        await db_session.refresh(transcribed)
        assert transcribed.status is LectureAudioStatus.TRANSCRIBING
        assert len(await _chunks(db_session, transcribed.id)) == 3

    async def test_two_chunks_finishing_together_consolidate_once(
        self, db_session: AsyncSession, transcribed, use_test_session, bucket
    ):
        results = await asyncio.gather(
            import_pipeline.consolidate_audio(transcribed.id),
            import_pipeline.consolidate_audio(transcribed.id),
            import_pipeline.consolidate_audio(transcribed.id),
        )

        result = await db_session.execute(
            select(LectureSegmentModel).where(
                LectureSegmentModel.lecture_id == transcribed.lecture_id
            )
        )
        assert len(list(result.scalars().all())) == 1
        assert len([value for value in results if value is not None]) == 1


    async def test_a_crash_mid_consolidation_rolls_the_audio_back(
        self, db_session: AsyncSession, transcribed, use_test_session, bucket, monkeypatch
    ):
        async def explode(db, lecture_id, sequence):
            raise RuntimeError("worker morreu")

        monkeypatch.setattr(import_pipeline, "sum_audio_duration_before", explode)

        with pytest.raises(RuntimeError):
            await import_pipeline.consolidate_audio(transcribed.id)

        db_session.expunge_all()
        audio = await db_session.get(LectureAudioModel, transcribed.id)
        assert audio.status is LectureAudioStatus.TRANSCRIBING
        assert len(await _chunks(db_session, transcribed.id)) == 3
        assert bucket.deleted == []

    async def test_after_the_rollback_a_new_attempt_succeeds(
        self, db_session: AsyncSession, transcribed, use_test_session, bucket, monkeypatch
    ):
        real = import_pipeline.sum_audio_duration_before

        async def explode(db, lecture_id, sequence):
            raise RuntimeError("worker morreu")

        monkeypatch.setattr(import_pipeline, "sum_audio_duration_before", explode)
        with pytest.raises(RuntimeError):
            await import_pipeline.consolidate_audio(transcribed.id)

        monkeypatch.setattr(import_pipeline, "sum_audio_duration_before", real)
        assert await import_pipeline.consolidate_audio(transcribed.id) is not None

        db_session.expunge_all()
        audio = await db_session.get(LectureAudioModel, transcribed.id)
        assert audio.status is LectureAudioStatus.DONE


@pytest_asyncio.fixture
async def two_audios(db_session: AsyncSession, test_user: dict) -> LectureModel:
    lecture = LectureModel(
        user_id=test_user["id"], title="Aula importada", status=LectureStatus.PROCESSING
    )
    db_session.add(lecture)
    await db_session.flush()

    for sequence in (1, 2):
        db_session.add(
            LectureAudioModel(
                lecture_id=lecture.id,
                sequence=sequence,
                object_key=f"lectures/{lecture.id}/imports/{sequence:02d}.mp3",
                original_filename=f"{sequence}.mp3",
                duration_seconds=300.0,
                status=LectureAudioStatus.TRANSCRIBING,
            )
        )
    await db_session.commit()
    await db_session.refresh(lecture)
    return lecture


async def _audios(db: AsyncSession, lecture_id) -> list[LectureAudioModel]:
    result = await db.execute(
        select(LectureAudioModel)
        .where(LectureAudioModel.lecture_id == lecture_id)
        .order_by(LectureAudioModel.sequence)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
class TestFinalizeLecture:
    async def test_an_audio_still_running_holds_the_lecture(
        self, db_session: AsyncSession, two_audios, use_test_session
    ):
        audios = await _audios(db_session, two_audios.id)
        audios[0].status = LectureAudioStatus.DONE
        await db_session.commit()

        assert await import_pipeline.finalize_lecture(two_audios.id) is None

        await db_session.refresh(two_audios)
        assert two_audios.status is LectureStatus.PROCESSING

    async def test_every_audio_done_completes_the_lecture_with_the_total_duration(
        self, db_session: AsyncSession, two_audios, use_test_session
    ):
        for audio in await _audios(db_session, two_audios.id):
            audio.status = LectureAudioStatus.DONE
        await db_session.commit()

        assert await import_pipeline.finalize_lecture(two_audios.id) is LectureStatus.COMPLETED

        await db_session.refresh(two_audios)
        assert two_audios.status is LectureStatus.COMPLETED
        assert two_audios.duration_seconds == 600.0

    async def test_one_failed_audio_fails_the_lecture(
        self, db_session: AsyncSession, two_audios, use_test_session
    ):
        audios = await _audios(db_session, two_audios.id)
        audios[0].status = LectureAudioStatus.DONE
        audios[1].status = LectureAudioStatus.FAILED
        await db_session.commit()

        assert await import_pipeline.finalize_lecture(two_audios.id) is LectureStatus.FAILED

        await db_session.refresh(two_audios)
        assert two_audios.status is LectureStatus.FAILED

    async def test_two_audios_finishing_together_finalize_once(
        self, db_session: AsyncSession, two_audios, use_test_session
    ):
        for audio in await _audios(db_session, two_audios.id):
            audio.status = LectureAudioStatus.DONE
        await db_session.commit()

        results = await asyncio.gather(
            import_pipeline.finalize_lecture(two_audios.id),
            import_pipeline.finalize_lecture(two_audios.id),
        )

        assert len([value for value in results if value is not None]) == 1
