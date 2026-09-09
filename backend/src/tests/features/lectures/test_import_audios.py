from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.lectures import tasks
from src.features.lectures.models import LectureAudioModel, LectureAudioStatus
from src.features.lectures.services import lecture_service


class _FakeBucket:
    def __init__(self) -> None:
        self.uploaded: list[str] = []
        self.deleted: list[str] = []

    def upload_stream(self, stream, name, *, length, folder, content_type):
        key = f"{folder}/{name}"
        self.uploaded.append(key)
        return SimpleNamespace(key=key)

    def delete(self, key: str) -> None:
        self.deleted.append(key)


@pytest.fixture
def bucket(monkeypatch) -> _FakeBucket:
    fake = _FakeBucket()
    monkeypatch.setattr(lecture_service, "get_bucket_service", lambda: fake)
    return fake


@pytest.fixture
def dispatched(monkeypatch) -> list:
    calls: list = []
    monkeypatch.setattr(tasks, "dispatch_import_lecture", calls.append)
    return calls


def _item(filename: str, duration: float) -> lecture_service.ImportAudioItem:
    return {
        "filename": filename,
        "stream": io.BytesIO(b"audio"),
        "size": 5,
        "content_type": "audio/mpeg",
        "duration": duration,
    }


async def _audios(db: AsyncSession, lecture_id) -> list[LectureAudioModel]:
    result = await db.execute(
        select(LectureAudioModel)
        .where(LectureAudioModel.lecture_id == lecture_id)
        .order_by(LectureAudioModel.sequence)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
class TestImportRecordsItsAudios:
    async def test_one_row_per_uploaded_file_in_order(
        self, db_session: AsyncSession, test_user: dict, bucket, dispatched
    ):
        summary = await lecture_service.start_import_lecture(
            db_session,
            user_id=test_user["id"],
            title="Aula importada",
            subject_id=None,
            audio_items=[_item("aula.mp3", 90.0), _item("continuacao.mp3", 45.5)],
        )

        audios = await _audios(db_session, summary.id)

        assert [audio.sequence for audio in audios] == [1, 2]
        assert [audio.original_filename for audio in audios] == ["aula.mp3", "continuacao.mp3"]
        assert [audio.duration_seconds for audio in audios] == [90.0, 45.5]
        assert [audio.object_key for audio in audios] == bucket.uploaded
        assert all(audio.status is LectureAudioStatus.PENDING for audio in audios)
        assert all(audio.transcribed_seconds == 0.0 for audio in audios)

    async def test_rows_survive_the_commit_that_precedes_dispatch(
        self, db_session: AsyncSession, test_user: dict, bucket, dispatched
    ):
        summary = await lecture_service.start_import_lecture(
            db_session,
            user_id=test_user["id"],
            title="Aula importada",
            subject_id=None,
            audio_items=[_item("aula.mp3", 90.0)],
        )

        db_session.expunge_all()
        audios = await _audios(db_session, summary.id)

        assert len(audios) == 1
        assert dispatched == [summary.id]

    async def test_an_upload_failure_leaves_no_audio_rows(
        self, db_session: AsyncSession, test_user: dict, bucket, dispatched, monkeypatch
    ):
        def explode(*args, **kwargs):
            raise RuntimeError("minio caiu")

        monkeypatch.setattr(bucket, "upload_stream", explode)

        with pytest.raises(HTTPException):
            await lecture_service.start_import_lecture(
                db_session,
                user_id=test_user["id"],
                title="Aula importada",
                subject_id=None,
                audio_items=[_item("aula.mp3", 90.0)],
            )

        result = await db_session.execute(select(LectureAudioModel))
        assert list(result.scalars().all()) == []
        assert dispatched == []
