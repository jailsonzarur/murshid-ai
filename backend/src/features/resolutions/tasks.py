from __future__ import annotations

from uuid import UUID

from src.core.celery import celery_app
from src.core.celery_async import run_async
from src.database import AsyncSessionLocal


@celery_app.task(name="evaluate_resolution_task")
def evaluate_resolution_task(resolution_id: str, user_id: str) -> None:
    run_async(_evaluate_resolution_task(UUID(resolution_id), UUID(user_id)))


async def _evaluate_resolution_task(resolution_id: UUID, user_id: UUID) -> None:
    from src.features.resolutions.services.evaluation_service import evaluate_resolution_responses

    async with AsyncSessionLocal() as db:
        await evaluate_resolution_responses(db, resolution_id=resolution_id, user_id=user_id)
