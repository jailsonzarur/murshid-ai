from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from src.features.subjects.models import (
    SubjectDocumentChunkModel,
    SubjectDocumentImageModel,
    SubjectDocumentIndexStatus,
    SubjectDocumentModel,
    SubjectModel,
)


async def get_subject_by_name(db: AsyncSession, user_id: UUID, name: str) -> SubjectModel | None:
    result = await db.execute(
        select(SubjectModel).where(SubjectModel.user_id == user_id, SubjectModel.name == name)
    )
    return result.scalar_one_or_none()


async def get_subject_by_id(db: AsyncSession, subject_id: UUID, user_id: UUID) -> SubjectModel | None:
    result = await db.execute(
        select(SubjectModel).where(SubjectModel.id == subject_id, SubjectModel.user_id == user_id)
    )
    return result.scalar_one_or_none()


def _search_filter(query, search: str | None):
    term = (search or "").strip()
    return query if not term else query.where(SubjectModel.name.ilike(f"%{term}%"))


async def count_subjects(db: AsyncSession, user_id: UUID, search: str | None = None) -> int:
    query = _search_filter(
        select(func.count()).select_from(SubjectModel).where(SubjectModel.user_id == user_id),
        search,
    )
    return (await db.execute(query)).scalar_one()


async def list_subjects(
    db: AsyncSession, user_id: UUID, *, offset: int = 0, limit: int | None = None
) -> list[SubjectModel]:
    query = (
        select(SubjectModel)
        .where(SubjectModel.user_id == user_id)
        .options(selectinload(SubjectModel.documents))
        .order_by(SubjectModel.name)
        .offset(offset)
    )
    if limit is not None:
        query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_subject_options(
    db: AsyncSession,
    user_id: UUID,
    *,
    offset: int = 0,
    limit: int | None = None,
    search: str | None = None,
) -> list[SubjectModel]:
    query = _search_filter(
        select(SubjectModel).where(SubjectModel.user_id == user_id).order_by(SubjectModel.name),
        search,
    ).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return list((await db.execute(query)).scalars().all())


def add_subject(db: AsyncSession, subject: SubjectModel) -> None:
    db.add(subject)


async def delete_subject(db: AsyncSession, subject: SubjectModel) -> None:
    await db.delete(subject)


async def list_subject_documents(db: AsyncSession, subject_id: UUID) -> list[SubjectDocumentModel]:
    result = await db.execute(
        select(SubjectDocumentModel)
        .where(SubjectDocumentModel.subject_id == subject_id)
        .order_by(SubjectDocumentModel.created_at)
    )
    return list(result.scalars().all())


async def get_subject_document(
    db: AsyncSession, document_id: UUID, user_id: UUID
) -> SubjectDocumentModel | None:
    result = await db.execute(
        select(SubjectDocumentModel)
        .join(SubjectModel, SubjectModel.id == SubjectDocumentModel.subject_id)
        .where(SubjectDocumentModel.id == document_id, SubjectModel.user_id == user_id)
    )
    return result.scalar_one_or_none()


def add_subject_document(db: AsyncSession, document: SubjectDocumentModel) -> None:
    db.add(document)


async def delete_subject_document(db: AsyncSession, document: SubjectDocumentModel) -> None:
    await db.delete(document)


async def get_subject_document_by_id(db: AsyncSession, document_id: UUID) -> SubjectDocumentModel | None:
    return await db.get(SubjectDocumentModel, document_id)


async def get_subjects_by_ids(
    db: AsyncSession, user_id: UUID, subject_ids: list[UUID]
) -> list[SubjectModel]:
    result = await db.execute(
        select(SubjectModel)
        .where(SubjectModel.user_id == user_id, SubjectModel.id.in_(subject_ids))
        .options(selectinload(SubjectModel.documents))
        .order_by(SubjectModel.name)
    )
    return list(result.scalars().all())


RECLAIMABLE_INDEX_STATUS = (SubjectDocumentIndexStatus.NONE, SubjectDocumentIndexStatus.FAILED)


def get_subject_document_by_id_sync(db: Session, document_id: UUID) -> SubjectDocumentModel | None:
    return db.get(SubjectDocumentModel, document_id)


def claim_document_for_indexing_sync(db: Session, document_id: UUID) -> bool:
    result = db.execute(
        update(SubjectDocumentModel)
        .where(
            SubjectDocumentModel.id == document_id,
            SubjectDocumentModel.index_status.in_(RECLAIMABLE_INDEX_STATUS),
        )
        .values(index_status=SubjectDocumentIndexStatus.REQUESTED)
        .returning(SubjectDocumentModel.id)
    )
    return result.scalar_one_or_none() is not None


def set_document_index_status_sync(
    db: Session, document_id: UUID, value: SubjectDocumentIndexStatus
) -> None:
    db.execute(
        update(SubjectDocumentModel)
        .where(SubjectDocumentModel.id == document_id)
        .values(index_status=value)
    )


def clear_document_index_sync(db: Session, document_id: UUID) -> None:
    db.execute(
        delete(SubjectDocumentImageModel).where(
            SubjectDocumentImageModel.document_id == document_id
        )
    )
    db.execute(
        delete(SubjectDocumentChunkModel).where(
            SubjectDocumentChunkModel.document_id == document_id
        )
    )


def add_document_chunk_sync(db: Session, chunk: SubjectDocumentChunkModel) -> None:
    db.add(chunk)


def add_document_image_sync(db: Session, image: SubjectDocumentImageModel) -> None:
    db.add(image)


def search_subject_chunks_sync(
    db: Session, subject_id: UUID, embedding: list[float], *, limit: int = 3
) -> list[tuple[SubjectDocumentChunkModel, float]]:
    distance = SubjectDocumentChunkModel.embedding.cosine_distance(embedding)
    result = db.execute(
        select(SubjectDocumentChunkModel, distance.label("distance"))
        .where(SubjectDocumentChunkModel.subject_id == subject_id)
        .order_by(distance)
        .limit(limit)
    )
    return [(chunk, float(value)) for chunk, value in result.all()]
