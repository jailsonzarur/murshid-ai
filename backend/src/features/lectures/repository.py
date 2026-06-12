from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.lectures.models import LectureEventModel, LectureEventType, LectureModel, LectureSegmentModel


async def create_lecture(db: AsyncSession, lecture: LectureModel) -> None:
    db.add(lecture)
    await db.flush()


async def get_lecture_by_id(db: AsyncSession, lecture_id: UUID) -> LectureModel | None:
    return await db.get(LectureModel, lecture_id)


async def get_lecture_with_events(db: AsyncSession, lecture_id: UUID) -> LectureModel | None:
    result = await db.execute(
        select(LectureModel)
        .where(LectureModel.id == lecture_id)
        .options(selectinload(LectureModel.events))
    )
    return result.scalar_one_or_none()


async def get_lecture_with_relations(db: AsyncSession, lecture_id: UUID) -> LectureModel | None:
    result = await db.execute(
        select(LectureModel)
        .where(LectureModel.id == lecture_id)
        .options(
            selectinload(LectureModel.events),
            selectinload(LectureModel.segments),
        )
    )
    return result.scalar_one_or_none()


async def list_lectures_for_user_with_counts(
    db: AsyncSession, user_id: UUID
) -> list[tuple[LectureModel, int, int]]:
    topics_count = func.coalesce(
        func.sum(case((LectureEventModel.type == LectureEventType.TOPIC, 1), else_=0)), 0
    ).label("topics_count")
    alerts_count = func.coalesce(
        func.sum(case((LectureEventModel.type == LectureEventType.ALERT, 1), else_=0)), 0
    ).label("alerts_count")

    stmt = (
        select(LectureModel, topics_count, alerts_count)
        .outerjoin(LectureEventModel, LectureEventModel.lecture_id == LectureModel.id)
        .where(LectureModel.user_id == user_id)
        .group_by(LectureModel.id)
        .order_by(LectureModel.created_at.desc())
    )
    result = await db.execute(stmt)
    return [(row[0], int(row[1]), int(row[2])) for row in result.all()]


async def add_segment(db: AsyncSession, segment: LectureSegmentModel) -> None:
    db.add(segment)
    await db.flush()


async def add_event(db: AsyncSession, event: LectureEventModel) -> None:
    db.add(event)
    await db.flush()
