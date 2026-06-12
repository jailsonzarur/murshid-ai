from __future__ import annotations

from uuid import UUID

from src.core.celery import celery_app
from src.core.celery_async import run_async
from src.database import AsyncSessionLocal


@celery_app.task(name="generate_lecture_summary_task")
def generate_lecture_summary_task(lecture_id: str) -> None:
    run_async(_generate_lecture_summary_task(UUID(lecture_id)))


async def _generate_lecture_summary_task(lecture_id: UUID) -> None:
    from src.features.lectures.services.lecture_service import generate_final_summary

    async with AsyncSessionLocal() as db:
        await generate_final_summary(db, lecture_id=lecture_id)
