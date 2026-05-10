from __future__ import annotations

import asyncio
import traceback
from collections.abc import Coroutine
from typing import Any, cast
from uuid import UUID

from celery.signals import worker_process_shutdown

from src.core.celery import celery_app
from src.database import AsyncSessionLocal, close_db
from src.features.exams.agents import ExamProcessingState, OriginalDocumentState
from src.features.exams.models import ExamModel, ExamStatus
from src.features.exams.repository import get_exam_with_documents

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
        original_docs = await _mark_exam_as_processing_and_get_documents(exam_id)

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

        await _set_exam_status(exam_id, ExamStatus.COMPLETED)
    except Exception:
        await _set_exam_status(exam_id, ExamStatus.FAILED, error_log=traceback.format_exc())
        raise


async def _mark_exam_as_processing_and_get_documents(exam_id: UUID) -> list[OriginalDocumentState]:
    async with AsyncSessionLocal() as db:
        exam = await get_exam_with_documents(db, exam_id)

        if exam is None:
            raise ValueError(f"Exam not found: {exam_id}")

        exam.status = ExamStatus.PROCESSING
        exam.error_log = None
        await db.commit()

        return [
            {
                "file_url": document.file_url,
                "mime_type": document.mime_type,
                "original_name": document.original_name,
                "page_order": document.page_order,
            }
            for document in sorted(exam.documents, key=lambda item: item.page_order)
        ]


async def _set_exam_status(exam_id: UUID, status: ExamStatus, *, error_log: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        exam = await db.get(ExamModel, exam_id)

        if exam is None:
            return

        exam.status = status
        exam.error_log = error_log
        await db.commit()
