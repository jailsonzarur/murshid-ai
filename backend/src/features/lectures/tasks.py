from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from src.core.celery import celery_app
from src.core.celery_async import run_async
from src.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_FILE_CONCURRENCY = 2


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
    from src.features.lectures.ai.transcription import WHISPER_CONCURRENCY, transcribe_audio_file
    from src.features.lectures.models import LectureSegmentModel, LectureStatus
    from src.features.lectures.repository import add_segment, get_lecture_with_segments
    from src.features.lectures.services.lecture_service import generate_final_summary

    bucket = get_bucket_service()
    transcription_ok = False

    file_sem = asyncio.Semaphore(_FILE_CONCURRENCY)
    whisper_sem = asyncio.Semaphore(WHISPER_CONCURRENCY)

    async def transcrever(item: dict) -> str:
        async with file_sem:
            audio = await asyncio.to_thread(bucket.get, item["object_key"])
            return await transcribe_audio_file(
                audio.content,
                item["object_key"].rsplit("/", 1)[-1],
                duration_hint=float(item["duration"]),
                semaphore=whisper_sem,
            )

    async with AsyncSessionLocal() as db:
        lecture = await get_lecture_with_segments(db, lecture_id)
        if lecture is None:
            logger.warning("process_imported_lecture_task: lecture %s not found", lecture_id)
            return

        next_sequence = (max((s.sequence for s in lecture.segments), default=0)) + 1
        uploaded_keys: list[str] = [item["object_key"] for item in items]

        try:
            transcripts = await asyncio.gather(*(transcrever(item) for item in items))

            for offset, (item, transcript) in enumerate(zip(items, transcripts)):
                duration = float(item["duration"])
                segment = LectureSegmentModel(
                    lecture=lecture,
                    sequence=next_sequence + offset,
                    transcript=transcript,
                    duration_seconds=duration,
                    offset_seconds=lecture.duration_seconds,
                )
                await add_segment(db, segment)
                lecture.duration_seconds += duration

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
