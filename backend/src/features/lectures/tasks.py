from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from celery.exceptions import MaxRetriesExceededError

from src.core.celery import celery_app
from src.core.celery_async import run_async

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _backoff(retries: int) -> int:
    return 10 * 2**retries


def _run_generate_summary(lecture_id: str) -> None:
    from src.features.lectures.services.lecture_service import generate_final_summary

    generate_final_summary(UUID(lecture_id))


@celery_app.task(name="generate_lecture_summary_task")
def generate_lecture_summary_task(lecture_id: str) -> None:
    _run_generate_summary(lecture_id)


def dispatch_import_lecture(lecture_id: UUID) -> None:
    cast(Any, start_import_lecture_task).delay(str(lecture_id))


@celery_app.task(bind=True, name="start_import_lecture_task", max_retries=MAX_RETRIES)
def start_import_lecture_task(self, lecture_id: str) -> None:
    from src.features.lectures.services.import_pipeline import start_import

    try:
        audio_ids = run_async(start_import(UUID(lecture_id)))
    except Exception:
        logger.exception("start_import_lecture_task: failed for lecture=%s", lecture_id)
        raise self.retry(countdown=_backoff(self.request.retries))

    for audio_id in audio_ids:
        cast(Any, chunk_audio_task).delay(str(audio_id))


@celery_app.task(name="finalize_lecture_task")
def finalize_lecture_task(lecture_id: str) -> None:
    from src.features.lectures.models import LectureStatus
    from src.features.lectures.services.import_pipeline import finalize_lecture

    outcome = run_async(finalize_lecture(UUID(lecture_id)))
    if outcome is LectureStatus.COMPLETED:
        cast(Any, generate_lecture_summary_task).delay(lecture_id)


@celery_app.task(bind=True, name="chunk_audio_task", max_retries=MAX_RETRIES)
def chunk_audio_task(self, audio_id: str) -> None:
    from src.features.lectures.services.import_pipeline import (
        chunk_audio,
        lecture_id_of_audio,
        mark_audio_failed,
    )

    try:
        chunk_ids = run_async(chunk_audio(UUID(audio_id)))
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        try:
            raise self.retry(countdown=_backoff(self.request.retries))
        except MaxRetriesExceededError:
            logger.exception("chunk_audio_task: gave up on audio=%s", audio_id)
            mark_audio_failed(UUID(audio_id), reason)
            _finalize(lecture_id_of_audio(UUID(audio_id)))
            return

    for chunk_id in chunk_ids:
        cast(Any, transcribe_chunk_task).delay(str(chunk_id))


def _run_transcribe_chunk(task, chunk_id: str) -> None:
    from src.features.lectures.ai.transcription import is_permanent_transcription_error
    from src.features.lectures.services.import_pipeline import fail_audio_of_chunk, transcribe_chunk

    try:
        audio_id = transcribe_chunk(UUID(chunk_id))
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        if is_permanent_transcription_error(exc):
            logger.error("transcribe_chunk_task: permanent failure on chunk=%s: %s", chunk_id, reason)
            _finalize(fail_audio_of_chunk(UUID(chunk_id), reason))
            return
        try:
            raise task.retry(countdown=_backoff(task.request.retries))
        except MaxRetriesExceededError:
            logger.exception("transcribe_chunk_task: gave up on chunk=%s", chunk_id)
            _finalize(fail_audio_of_chunk(UUID(chunk_id), reason))
            return

    if audio_id is not None:
        cast(Any, consolidate_audio_task).delay(str(audio_id))


@celery_app.task(bind=True, name="transcribe_chunk_task", max_retries=MAX_RETRIES)
def transcribe_chunk_task(self, chunk_id: str) -> None:
    _run_transcribe_chunk(self, chunk_id)


@celery_app.task(name="consolidate_audio_task")
def consolidate_audio_task(audio_id: str) -> None:
    from src.features.lectures.services.import_pipeline import consolidate_audio

    _finalize(run_async(consolidate_audio(UUID(audio_id))))


def _finalize(lecture_id: UUID | None) -> None:
    if lecture_id is not None:
        cast(Any, finalize_lecture_task).delay(str(lecture_id))
