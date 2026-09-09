from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.lectures.models import (
    LectureAudioChunkModel,
    LectureAudioModel,
    LectureAudioStatus,
    LectureModel,
    LectureSegmentModel,
    LectureStatus,
)


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


async def add_audios(db: AsyncSession, audios: list[LectureAudioModel]) -> None:
    db.add_all(audios)
    await db.flush()


async def get_audio(db: AsyncSession, audio_id: UUID) -> LectureAudioModel | None:
    return await db.get(LectureAudioModel, audio_id)


async def get_audio_with_chunks(db: AsyncSession, audio_id: UUID) -> LectureAudioModel | None:
    result = await db.execute(
        select(LectureAudioModel)
        .where(LectureAudioModel.id == audio_id)
        .options(selectinload(LectureAudioModel.chunks))
    )
    return result.scalar_one_or_none()


async def claim_audio_for_consolidation(db: AsyncSession, audio_id: UUID) -> bool:
    pending = (
        select(LectureAudioChunkModel.id)
        .where(
            LectureAudioChunkModel.audio_id == audio_id,
            LectureAudioChunkModel.transcript.is_(None),
        )
        .exists()
    )
    result = await db.execute(
        update(LectureAudioModel)
        .where(
            LectureAudioModel.id == audio_id,
            LectureAudioModel.status == LectureAudioStatus.TRANSCRIBING,
            ~pending,
        )
        .values(status=LectureAudioStatus.DONE)
        .returning(LectureAudioModel.id)
    )
    return result.scalar_one_or_none() is not None


async def sum_audio_duration_before(db: AsyncSession, lecture_id: UUID, sequence: int) -> float:
    result = await db.execute(
        select(func.coalesce(func.sum(LectureAudioModel.duration_seconds), 0.0)).where(
            LectureAudioModel.lecture_id == lecture_id,
            LectureAudioModel.sequence < sequence,
        )
    )
    return float(result.scalar_one())


async def list_audio_ids_for_lecture(db: AsyncSession, lecture_id: UUID) -> list[UUID]:
    result = await db.execute(
        select(LectureAudioModel.id)
        .where(LectureAudioModel.lecture_id == lecture_id)
        .order_by(LectureAudioModel.sequence)
    )
    return list(result.scalars().all())


async def claim_lecture_finalization(db: AsyncSession, lecture_id: UUID) -> LectureStatus | None:
    def _audios(*conditions):
        return select(LectureAudioModel.id).where(
            LectureAudioModel.lecture_id == lecture_id, *conditions
        )

    has_audio = _audios().exists()
    in_flight = _audios(
        LectureAudioModel.status.notin_([LectureAudioStatus.DONE, LectureAudioStatus.FAILED])
    ).exists()
    any_failed = _audios(LectureAudioModel.status == LectureAudioStatus.FAILED).exists()

    settled = (
        LectureModel.id == lecture_id,
        LectureModel.status == LectureStatus.PROCESSING,
        has_audio,
        ~in_flight,
    )

    failed = await db.execute(
        update(LectureModel)
        .where(*settled, any_failed)
        .values(status=LectureStatus.FAILED)
        .returning(LectureModel.id)
    )
    if failed.scalar_one_or_none() is not None:
        return LectureStatus.FAILED

    total = (
        select(func.coalesce(func.sum(LectureAudioModel.duration_seconds), 0.0))
        .where(LectureAudioModel.lecture_id == lecture_id)
        .scalar_subquery()
    )
    completed = await db.execute(
        update(LectureModel)
        .where(*settled, ~any_failed)
        .values(status=LectureStatus.COMPLETED, duration_seconds=total)
        .returning(LectureModel.id)
    )
    if completed.scalar_one_or_none() is not None:
        return LectureStatus.COMPLETED

    return None


async def get_audio_chunk(db: AsyncSession, chunk_id: UUID) -> LectureAudioChunkModel | None:
    return await db.get(LectureAudioChunkModel, chunk_id)


async def add_segment(db: AsyncSession, segment: LectureSegmentModel) -> None:
    db.add(segment)
    await db.flush()


async def delete_lecture(db: AsyncSession, lecture: LectureModel) -> None:
    await db.delete(lecture)
