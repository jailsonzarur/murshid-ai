from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
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
    return [SubjectDocumentSchema.from_model(document) for document in documents]


async def remove_document(db: AsyncSession, document_id: UUID, user_id: UUID) -> None:
    document = await get_subject_document(db, document_id, user_id)
    if document is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Documento não encontrado.")

    keys = [document.object_key, document.thumbnail_key, document.icon_key]
    await delete_subject_document(db, document)
    await db.commit()

    bucket = get_bucket_service()
    for key in keys:
        if not key:
            continue
        try:
            bucket.delete(key)
        except Exception:
            logger.exception("remove_document: failed to delete %s", key)


async def _upload_png(
    bucket: object, content: bytes | None, name: str, folder: str
) -> str | None:
    if not content:
        return None
    upload = await asyncio.to_thread(
        bucket.upload,  # type: ignore[attr-defined]
        content,
        name,
        folder=folder,
        content_type="image/png",
    )
    return upload.key


async def ingest_document(document_id: UUID) -> None:
    """Gera a capa e conta as páginas. Roda no worker, fora do ciclo da request."""
    from src.database import AsyncSessionLocal
    from src.features.subjects.ai.document_ingestion import build_preview
    from src.features.subjects.models import SubjectDocumentStatus
    from src.features.subjects.repository import get_subject_document_by_id

    async with AsyncSessionLocal() as db:
        document = await get_subject_document_by_id(db, document_id)
        if document is None:
            logger.warning("ingest_document: document %s not found", document_id)
            return
        # só READY encerra: PROCESSING precisa passar para que o retry funcione
        if document.status == SubjectDocumentStatus.READY:
            return

        document.status = SubjectDocumentStatus.PROCESSING
        document.error_log = None
        await db.commit()

        object_key = document.object_key
        mime_type = document.mime_type
        original_name = document.original_name
        subject_id = document.subject_id

    bucket = get_bucket_service()
    with tempfile.TemporaryDirectory(prefix="subject-doc-") as tmp:
        source_path = Path(tmp) / original_name
        await asyncio.to_thread(bucket.download_to, object_key, source_path)
        preview = await asyncio.to_thread(build_preview, source_path, mime_type)

        stem = Path(original_name).stem
        thumbnail_key = await _upload_png(
            bucket, preview.thumbnail_png, f"{stem}.png", f"subjects/{subject_id}/thumbnails"
        )
        icon_key = await _upload_png(
            bucket, preview.icon_png, f"{stem}-icon.png", f"subjects/{subject_id}/icons"
        )

    async with AsyncSessionLocal() as db:
        document = await get_subject_document_by_id(db, document_id)
        if document is None:
            for key in (thumbnail_key, icon_key):
                if key:
                    await asyncio.to_thread(bucket.delete, key)
            return

        document.page_count = preview.page_count
        document.thumbnail_key = thumbnail_key
        document.icon_key = icon_key
        document.status = SubjectDocumentStatus.READY
        await db.commit()

    logger.info("ingest_document done for %s: pages=%s", document_id, preview.page_count)


async def mark_document_failed(document_id: UUID, message: str) -> None:
    from src.database import AsyncSessionLocal
    from src.features.subjects.models import SubjectDocumentStatus
    from src.features.subjects.repository import get_subject_document_by_id

    async with AsyncSessionLocal() as db:
        document = await get_subject_document_by_id(db, document_id)
        if document is None:
            return
        document.status = SubjectDocumentStatus.FAILED
        document.error_log = message[:2000]
        await db.commit()
