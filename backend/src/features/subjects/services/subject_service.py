from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.subjects.models import SubjectModel
from src.features.subjects.repository import (
    add_subject,
    add_subject_document,
    delete_subject,
    get_subject_by_id,
    get_subject_by_name,
    list_subjects,
)
from src.features.subjects.schemas.subject_schemas import (
    SubjectDetailSchema,
    SubjectSchema,
    UpdateSubjectSchema,
)
from src.features.subjects.services.subject_document_service import (
    discard_stored_documents,
    store_documents,
)
from src.features.subjects.tasks import ingest_subject_document_task

_DUPLICATE_NAME = "Já existe uma matéria com esse nome."
_NOT_FOUND = "Matéria não encontrada."


def _normalize_name(raw: str) -> str:
    return " ".join(raw.strip().split())[:100]


def _error(status_code: int, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "errors": [message], "data": None},
    )


async def _require_subject(db: AsyncSession, subject_id: UUID, user_id: UUID) -> SubjectModel:
    subject = await get_subject_by_id(db, subject_id, user_id)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    return subject


async def list_all_subjects(db: AsyncSession, user_id: UUID) -> list[SubjectSchema]:
    subjects = await list_subjects(db, user_id)
    return [SubjectSchema.model_validate(subject) for subject in subjects]


async def create_subject(
    db: AsyncSession,
    user_id: UUID,
    *,
    name: str,
    documents: list[UploadFile],
) -> SubjectDetailSchema:
    normalized = _normalize_name(name)
    if not normalized:
        raise _error(status.HTTP_400_BAD_REQUEST, "Nome inválido.")

    if await get_subject_by_name(db, user_id, normalized) is not None:
        raise _error(status.HTTP_409_CONFLICT, _DUPLICATE_NAME)

    subject = SubjectModel(user_id=user_id, name=normalized)
    add_subject(db, subject)
    await db.flush()

    stored = await store_documents(subject.id, documents)
    for document in stored:
        add_subject_document(db, document)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        discard_stored_documents(stored)
        raise _error(status.HTTP_409_CONFLICT, _DUPLICATE_NAME)
    except Exception:
        await db.rollback()
        discard_stored_documents(stored)
        raise

    await db.refresh(subject, ["documents"])

    for document in subject.documents:
        cast(Any, ingest_subject_document_task).delay(str(document.id))

    return SubjectDetailSchema.model_validate(subject)


async def update_subject(
    db: AsyncSession,
    *,
    subject_id: UUID,
    user_id: UUID,
    payload: UpdateSubjectSchema,
) -> SubjectSchema:
    subject = await _require_subject(db, subject_id, user_id)

    normalized = _normalize_name(payload.name)
    if not normalized:
        raise _error(status.HTTP_400_BAD_REQUEST, "Nome inválido.")

    if normalized != subject.name:
        if await get_subject_by_name(db, user_id, normalized) is not None:
            raise _error(status.HTTP_409_CONFLICT, _DUPLICATE_NAME)

    subject.name = normalized
    await db.commit()
    await db.refresh(subject)
    return SubjectSchema.model_validate(subject)


async def remove_subject(db: AsyncSession, subject_id: UUID, user_id: UUID) -> None:
    subject = await _require_subject(db, subject_id, user_id)
    await delete_subject(db, subject)
    await db.commit()
