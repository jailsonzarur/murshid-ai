from __future__ import annotations

import logging
from uuid import UUID

from src.core.celery import celery_app
from src.core.celery_async import run_async
from src.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="generate_lecture_summary_task")
def generate_lecture_summary_task(lecture_id: str) -> None:
    run_async(_generate_lecture_summary_task(UUID(lecture_id)))


async def _generate_lecture_summary_task(lecture_id: UUID) -> None:
    from src.features.lectures.services.lecture_service import generate_final_summary

    await generate_final_summary(lecture_id)


@celery_app.task(name="process_imported_lecture_task")
def process_imported_lecture_task(lecture_id: str, items: list[dict]) -> None:
    """Transcribes ordered audio files for an imported lecture.

    `items`: list of dicts with keys `object_key` (str) and `duration` (float),
    in the order the audios were uploaded.
    """
    run_async(_process_imported_lecture_task(UUID(lecture_id), items))


async def _process_imported_lecture_task(lecture_id: UUID, items: list[dict]) -> None:
    from src.features.files.services.bucket_service import get_bucket_service
    from src.features.lectures.models import LectureStatus
    from src.features.lectures.repository import get_lecture_with_segments
    from src.features.lectures.services.lecture_service import (
        _transcribe_and_persist_segment,
        generate_final_summary,
    )

    bucket = get_bucket_service()
    transcription_ok = False

    async with AsyncSessionLocal() as db:
        lecture = await get_lecture_with_segments(db, lecture_id)
        if lecture is None:
            logger.warning("process_imported_lecture_task: lecture %s not found", lecture_id)
            return

        next_sequence = (max((s.sequence for s in lecture.segments), default=0)) + 1
        uploaded_keys: list[str] = [item["object_key"] for item in items]

        try:
            for offset, item in enumerate(items):
                object_key: str = item["object_key"]
                duration = float(item["duration"])
                try:
                    audio_obj = bucket.get(object_key)
                except Exception:
                    logger.exception(
                        "process_imported_lecture_task: failed to fetch %s", object_key
                    )
                    lecture.status = LectureStatus.FAILED
                    await db.commit()
                    return

                await _transcribe_and_persist_segment(
                    db,
                    lecture,
                    audio_bytes=audio_obj.content,
                    filename=object_key.rsplit("/", 1)[-1],
                    sequence=next_sequence + offset,
                    duration=duration,
                )

            lecture.status = LectureStatus.COMPLETED
            await db.commit()
            transcription_ok = True
        except Exception:
            logger.exception("process_imported_lecture_task: failed lecture %s", lecture_id)
            lecture.status = LectureStatus.FAILED
            await db.commit()
            return
        finally:
            for key in uploaded_keys:
                try:
                    bucket.delete(key)
                except Exception:
                    logger.exception("process_imported_lecture_task: failed to delete %s", key)

    if not transcription_ok:
        return

    await generate_final_summary(lecture_id)
