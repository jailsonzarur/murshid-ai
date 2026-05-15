from __future__ import annotations

import asyncio
import traceback
from collections.abc import Coroutine
from typing import Any, cast
from uuid import UUID

from celery.signals import worker_process_shutdown

from src.core.celery import celery_app
from src.database import close_db
from src.features.exams.agents import ExamProcessingState
from src.features.exams.models import ExamStatus
from src.features.exams.services.exam_service import mark_exam_as_processing_and_get_documents, set_exam_status

_worker_loop: asyncio.AbstractEventLoop | None = None


@celery_app.task(name="process_exam_task")
def process_exam_task(exam_id: str) -> None:
    _run_async(_process_exam_task(UUID(exam_id)))


def _run_async(coro: Coroutine[Any, Any, None]) -> None:
    loop = _get_or_create_worker_loop()
    loop.run_until_complete(coro)


def _get_or_create_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop

    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)

    return _worker_loop


@worker_process_shutdown.connect
def _shutdown_worker_loop(**_: Any) -> None:
    if _worker_loop is None or _worker_loop.is_closed():
        return

    _worker_loop.run_until_complete(close_db())
    _worker_loop.close()


async def _process_exam_task(exam_id: UUID) -> None:
    try:
        original_docs = await mark_exam_as_processing_and_get_documents(exam_id)

        from src.features.exams.agents import run_exam_processing_graph

        await run_exam_processing_graph(
            cast(
                ExamProcessingState,
                {
                    "exam_id": exam_id,
                    "original_docs": original_docs,
                    "layout_elements": {},
                    "annotated_pages_base64": [],
                    "original_pages_base64": [],
                },
            )
        )

        await set_exam_status(exam_id, ExamStatus.COMPLETED)
    except Exception:
        await set_exam_status(exam_id, ExamStatus.FAILED, error_log=traceback.format_exc())
        raise
