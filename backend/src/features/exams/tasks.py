from __future__ import annotations

import traceback
from typing import cast
from uuid import UUID

from src.core.celery import celery_app
from src.core.celery_async import run_async
from src.features.exams.agents import ExamProcessingState
from src.features.exams.models import ExamStatus
from src.features.exams.services.exam_service import mark_exam_as_processing_and_get_documents, set_exam_status


@celery_app.task(name="process_exam_task")
def process_exam_task(exam_id: str) -> None:
    run_async(_process_exam_task(UUID(exam_id)))


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
