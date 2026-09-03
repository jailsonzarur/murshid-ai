from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from celery import chord

from src.core.celery import celery_app
from src.core.celery_async import run_async
from src.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


@celery_app.task(name="generate_lecture_summary_task")
def generate_lecture_summary_task(lecture_id: str) -> None:
    run_async(_generate_lecture_summary_task(UUID(lecture_id)))


async def _generate_lecture_summary_task(lecture_id: UUID) -> None:
    from src.features.lectures.services.lecture_service import generate_final_summary

    await generate_final_summary(lecture_id)


def dispatch_import_lecture(lecture_id: UUID, items: list[dict]) -> None:
    chord(cast(Any, transcribe_import_file_task).s(str(lecture_id), item) for item in items)(
        cast(Any, finalize_import_lecture_task).s(str(lecture_id))
    )


@celery_app.task(bind=True, name="transcribe_import_file_task", max_retries=MAX_RETRIES)
def transcribe_import_file_task(self, lecture_id: str, item: dict) -> dict | None:
    object_key = item["object_key"]

    try:
        transcript = run_async(_transcribe_import_file(item))
    except Exception as exc:
        if self.request.retries >= MAX_RETRIES:
            logger.exception(
                "transcribe_import_file_task: gave up on lecture=%s file=%s", lecture_id, object_key
            )
            _delete_object(object_key)
            return None
        raise self.retry(exc=exc, countdown=10 * 2**self.request.retries)

    _delete_object(object_key)
    return {"transcript": transcript, "duration": float(item["duration"])}


async def _transcribe_import_file(item: dict) -> str:
    import asyncio
    import tempfile
    from pathlib import Path

    from src.features.files.services.bucket_service import get_bucket_service
    from src.features.lectures.ai.transcription import transcribe_audio_file

    bucket = get_bucket_service()
    with tempfile.TemporaryDirectory(prefix="whisper-import-") as tmp:
        src_path = Path(tmp) / item["object_key"].rsplit("/", 1)[-1]
        await asyncio.to_thread(bucket.download_to, item["object_key"], src_path)
        return await transcribe_audio_file(src_path, duration_hint=float(item["duration"]))


def _delete_object(object_key: str) -> None:
    from src.features.files.services.bucket_service import get_bucket_service

    try:
        get_bucket_service().delete(object_key)
    except Exception:
        logger.exception("transcribe_import_file_task: failed to delete %s", object_key)


@celery_app.task(name="finalize_import_lecture_task")
def finalize_import_lecture_task(results: list[dict | None], lecture_id: str) -> None:
    run_async(_finalize_import_lecture(results, UUID(lecture_id)))


async def _finalize_import_lecture(results: list[dict | None], lecture_id: UUID) -> None:
    from src.features.lectures.models import LectureSegmentModel, LectureStatus
    from src.features.lectures.repository import add_segment, get_lecture_with_segments

    async with AsyncSessionLocal() as db:
        lecture = await get_lecture_with_segments(db, lecture_id)
        if lecture is None:
            logger.warning("finalize_import_lecture_task: lecture %s not found", lecture_id)
            return

        if lecture.status != LectureStatus.PROCESSING:
            return

        transcribed = [result for result in results if result is not None]
        if len(transcribed) != len(results):
            lecture.status = LectureStatus.FAILED
            await db.commit()
            return

        next_sequence = max((segment.sequence for segment in lecture.segments), default=0) + 1

        for offset, result in enumerate(transcribed):
            duration = float(result["duration"])
            await add_segment(
                db,
                LectureSegmentModel(
                    lecture=lecture,
                    sequence=next_sequence + offset,
                    transcript=result["transcript"],
                    duration_seconds=duration,
                    offset_seconds=lecture.duration_seconds,
                ),
            )
            lecture.duration_seconds += duration

        lecture.status = LectureStatus.COMPLETED
        await db.commit()

    cast(Any, generate_lecture_summary_task).delay(str(lecture_id))
