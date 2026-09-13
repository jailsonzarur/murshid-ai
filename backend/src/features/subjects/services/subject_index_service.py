from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from uuid import UUID

from src.core.pipeline_log import short, stage
from src.database import SessionLocal
from src.features.files.services.bucket_service import get_bucket_service
from src.features.subjects.ai.chunking import Chunk, chunk_sections
from src.features.subjects.ai.embedding import embed_texts
from src.features.subjects.ai.heading_detection import split_into_sections
from src.features.subjects.ai.text_extraction import extract_elements
from src.features.subjects.models import (
    SubjectDocumentChunkModel,
    SubjectDocumentImageModel,
    SubjectDocumentIndexStatus,
)
from src.features.subjects.repository import (
    add_document_chunk_sync,
    add_document_image_sync,
    claim_document_for_indexing_sync,
    clear_document_index_sync,
    get_subject_document_by_id_sync,
    set_document_index_status_sync,
)

logger = logging.getLogger(__name__)


def claim_document_for_indexing(document_id: UUID) -> bool:
    """Só quem ganha a linha despacha a task, então clicar de novo ou reprocessar
    um upload não duplica trabalho."""
    with SessionLocal() as db:
        claimed = claim_document_for_indexing_sync(db, document_id)
        db.commit()
        return claimed


def index_document(document_id: UUID) -> None:
    with stage("index_document", document=short(document_id)):
        _index_document(document_id)


def _index_document(document_id: UUID) -> None:
    with SessionLocal() as db:
        document = get_subject_document_by_id_sync(db, document_id)
        if document is None:
            logger.warning("index_document: document %s not found", document_id)
            return
        if document.index_status == SubjectDocumentIndexStatus.DONE:
            return

        document.index_status = SubjectDocumentIndexStatus.PROCESSING
        db.commit()

        object_key = document.object_key
        original_name = document.original_name
        title = document.title
        subject_id = document.subject_id

    chunks = _build_chunks(object_key, original_name, title)
    if not chunks:
        logger.warning("index_document: no chunks for %s", document_id)
        set_failed(document_id)
        return

    vectors = embed_texts([f"{chunk.heading_path}\n{chunk.text}" for chunk in chunks])

    _persist(document_id, subject_id, chunks, vectors)
    logger.info("index_document done for %s: chunks=%d", document_id, len(chunks))


def _build_chunks(object_key: str, original_name: str, title: str) -> list[Chunk]:
    bucket = get_bucket_service()
    with tempfile.TemporaryDirectory(prefix="subject-index-") as tmp:
        source_path = Path(tmp) / original_name
        bucket.download_to(object_key, source_path)
        elements = extract_elements(source_path)

    return chunk_sections(split_into_sections(elements, title))


def _persist(
    document_id: UUID, subject_id: UUID, chunks: list[Chunk], vectors: list[list[float]]
) -> None:
    with SessionLocal() as db:
        clear_document_index_sync(db, document_id)

        for sequence, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True), start=1):
            row = SubjectDocumentChunkModel(
                document_id=document_id,
                subject_id=subject_id,
                sequence=sequence,
                text=chunk.text,
                heading_path=chunk.heading_path,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                embedding=vector,
            )
            add_document_chunk_sync(db, row)
            db.flush()

            for figure in chunk.figures:
                add_document_image_sync(
                    db,
                    SubjectDocumentImageModel(
                        document_id=document_id,
                        chunk_id=row.id,
                        page=figure.page,
                        bbox={
                            "x0": figure.bbox[0],
                            "y0": figure.bbox[1],
                            "x1": figure.bbox[2],
                            "y1": figure.bbox[3],
                        },
                        caption=figure.caption,
                    ),
                )

        document = get_subject_document_by_id_sync(db, document_id)
        if document is not None:
            document.index_status = SubjectDocumentIndexStatus.DONE
            document.chunk_count = len(chunks)

        db.commit()


def set_failed(document_id: UUID) -> None:
    with SessionLocal() as db:
        set_document_index_status_sync(db, document_id, SubjectDocumentIndexStatus.FAILED)
        db.commit()
