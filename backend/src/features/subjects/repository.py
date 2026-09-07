from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.subjects.models import SubjectDocumentModel, SubjectModel


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


async def count_subjects(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(SubjectModel).where(SubjectModel.user_id == user_id)
    )
    return result.scalar_one()


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


async def list_subject_options(db: AsyncSession, user_id: UUID) -> list[SubjectModel]:
    result = await db.execute(
        select(SubjectModel).where(SubjectModel.user_id == user_id).order_by(SubjectModel.name)
    )
    return list(result.scalars().all())


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
