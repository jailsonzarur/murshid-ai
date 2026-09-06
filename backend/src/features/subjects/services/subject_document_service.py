from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.files.services.bucket_service import get_bucket_service
from src.features.subjects.models import SubjectDocumentModel
from src.features.subjects.repository import (
    delete_subject_document,
    get_subject_by_id,
    get_subject_document,
    list_subject_documents,
)
from src.features.subjects.schemas.subject_schemas import SubjectDocumentSchema

logger = logging.getLogger(__name__)

MAX_DOCUMENTS = 10
MAX_DOCUMENT_BYTES = 50 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
}


def _error(status_code: int, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "errors": [message], "data": None},
    )


def validate_documents(documents: list[UploadFile]) -> None:
    if len(documents) > MAX_DOCUMENTS:
        raise _error(status.HTTP_400_BAD_REQUEST, f"Envie no máximo {MAX_DOCUMENTS} documentos.")

    for document in documents:
        if (document.content_type or "") not in ALLOWED_MIME_TYPES:
            raise _error(status.HTTP_400_BAD_REQUEST, "Formato não suportado. Envie PDF, TXT ou Markdown.")

        size_bytes = document.size or 0
        if size_bytes <= 0:
            raise _error(status.HTTP_400_BAD_REQUEST, f"Arquivo vazio: {document.filename}.")
        if size_bytes > MAX_DOCUMENT_BYTES:
            raise _error(status.HTTP_400_BAD_REQUEST, f"{document.filename} passa de 50 MB.")


async def store_documents(subject_id: UUID, documents: list[UploadFile]) -> list[SubjectDocumentModel]:
    """Sobe os arquivos pro bucket. Em falha, remove o que já subiu e propaga."""
    bucket = get_bucket_service()
    stored: list[SubjectDocumentModel] = []

    try:
        for document in documents:
            original_name = (document.filename or "documento")[:255]
            upload = await asyncio.to_thread(
                bucket.upload_stream,
                document.file,
                original_name,
                length=document.size or 0,
                folder=f"subjects/{subject_id}/documents",
                content_type=document.content_type,
            )
            stored.append(
                SubjectDocumentModel(
                    subject_id=subject_id,
                    title=original_name.rsplit(".", 1)[0],
                    original_name=original_name,
                    object_key=upload.key,
                    mime_type=document.content_type or "",
                    size_bytes=document.size or 0,
                )
            )
    except Exception:
        discard_stored_documents(stored)
        raise

    return stored


def discard_stored_documents(documents: list[SubjectDocumentModel]) -> None:
    bucket = get_bucket_service()
    for document in documents:
        try:
            bucket.delete(document.object_key)
        except Exception:
            logger.exception("discard_stored_documents: failed to delete %s", document.object_key)


async def list_documents(
    db: AsyncSession, subject_id: UUID, user_id: UUID
) -> list[SubjectDocumentSchema]:
    if await get_subject_by_id(db, subject_id, user_id) is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Matéria não encontrada.")
    documents = await list_subject_documents(db, subject_id)
    return [SubjectDocumentSchema.model_validate(document) for document in documents]


async def remove_document(db: AsyncSession, document_id: UUID, user_id: UUID) -> None:
    document = await get_subject_document(db, document_id, user_id)
    if document is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Documento não encontrado.")

    object_key = document.object_key
    await delete_subject_document(db, document)
    await db.commit()

    try:
        get_bucket_service().delete(object_key)
    except Exception:
        logger.exception("remove_document: failed to delete %s", object_key)
