from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.lectures.models import LectureModel, LectureSegmentModel


async def create_lecture(db: AsyncSession, lecture: LectureModel) -> None:
    db.add(lecture)
    await db.flush()


async def get_lecture_by_id(db: AsyncSession, lecture_id: UUID) -> LectureModel | None:
    return await db.get(LectureModel, lecture_id)


async def get_lecture_with_segments(db: AsyncSession, lecture_id: UUID) -> LectureModel | None:
    result = await db.execute(
        select(LectureModel)
        .where(LectureModel.id == lecture_id)
        .options(selectinload(LectureModel.segments))
    )
    return result.scalar_one_or_none()


async def list_lectures_for_user(db: AsyncSession, user_id: UUID) -> list[LectureModel]:
    result = await db.execute(
        select(LectureModel)
        .where(LectureModel.user_id == user_id)
        .order_by(LectureModel.created_at.desc())
    )
    return list(result.scalars().all())


async def add_segment(db: AsyncSession, segment: LectureSegmentModel) -> None:
    db.add(segment)
    await db.flush()


async def delete_lecture(db: AsyncSession, lecture: LectureModel) -> None:
    await db.delete(lecture)
