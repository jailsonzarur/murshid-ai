from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from src.core.celery import celery_app
from src.core.celery_async import run_async

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


@celery_app.task(bind=True, name="ingest_subject_document_task", max_retries=MAX_RETRIES)
def ingest_subject_document_task(self, document_id: str) -> None:
    from src.features.subjects.services.subject_document_service import ingest_document

    try:
        run_async(ingest_document(UUID(document_id)))
    except Exception as exc:
        if self.request.retries >= MAX_RETRIES:
            logger.exception("ingest_subject_document_task: gave up on %s", document_id)
            run_async(_mark_failed(UUID(document_id), str(exc)))
            return
        raise self.retry(exc=exc, countdown=10 * 2**self.request.retries)


@celery_app.task(bind=True, name="index_subject_document_task", max_retries=MAX_RETRIES)
def index_subject_document_task(self, document_id: str) -> None:
    from src.features.subjects.services.subject_index_service import index_document, set_failed

    try:
        index_document(UUID(document_id))
    except Exception as exc:
        if self.request.retries >= MAX_RETRIES:
            logger.exception("index_subject_document_task: gave up on %s", document_id)
            set_failed(UUID(document_id))
            return
        raise self.retry(exc=exc, countdown=30 * 2**self.request.retries)


def dispatch_index_document(document_id: UUID) -> None:
    from src.features.subjects.services.subject_index_service import (
        claim_document_for_indexing,
    )

    if claim_document_for_indexing(document_id):
        cast(Any, index_subject_document_task).delay(str(document_id))


async def _mark_failed(document_id: UUID, message: str) -> None:
    from src.features.subjects.services.subject_document_service import mark_document_failed

    await mark_document_failed(document_id, message)
