from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.exams.models import ExamModel
from src.features.questions.models import QuestionModel
from src.features.resolutions.models import (
    ExamResolutionModel,
    ExamResolutionStatus,
    QuestionResponseItemModel,
    QuestionResponseModel,
)

ACTIVE_RESOLUTION_STATUSES = {
    ExamResolutionStatus.IN_PROGRESS,
    ExamResolutionStatus.PAUSED,
}


async def get_active_resolution(
    db: AsyncSession,
    *,
    exam_id: UUID,
    user_id: UUID,
) -> ExamResolutionModel | None:
    result = await db.execute(
        select(ExamResolutionModel)
        .where(
            ExamResolutionModel.exam_id == exam_id,
            ExamResolutionModel.user_id == user_id,
            ExamResolutionModel.status.in_(ACTIVE_RESOLUTION_STATUSES),
        )
        .order_by(ExamResolutionModel.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_resolutions_for_exam(
    db: AsyncSession,
    *,
    exam_id: UUID,
    user_id: UUID,
) -> list[ExamResolutionModel]:
    result = await db.execute(
        select(ExamResolutionModel)
        .where(
            ExamResolutionModel.exam_id == exam_id,
            ExamResolutionModel.user_id == user_id,
        )
        .order_by(ExamResolutionModel.created_at.desc())
    )
    return list(result.scalars().all())


async def get_exam_for_resolution(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .options(selectinload(ExamModel.questions).selectinload(QuestionModel.options))
        .where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def get_resolution_by_id(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ExamResolutionModel | None:
    result = await db.execute(
        select(ExamResolutionModel).where(
            ExamResolutionModel.id == resolution_id,
            ExamResolutionModel.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_resolution_for_submit(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ExamResolutionModel | None:
    result = await db.execute(
        select(ExamResolutionModel)
        .options(
            selectinload(ExamResolutionModel.exam).selectinload(ExamModel.questions),
            selectinload(ExamResolutionModel.responses).selectinload(QuestionResponseModel.evaluations),
        )
        .where(
            ExamResolutionModel.id == resolution_id,
            ExamResolutionModel.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_resolution_for_detail(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ExamResolutionModel | None:
    result = await db.execute(
        select(ExamResolutionModel)
        .options(
            selectinload(ExamResolutionModel.exam)
            .selectinload(ExamModel.questions)
            .selectinload(QuestionModel.options),
            selectinload(ExamResolutionModel.responses)
            .selectinload(QuestionResponseModel.items)
            .selectinload(QuestionResponseItemModel.option),
            selectinload(ExamResolutionModel.responses).selectinload(QuestionResponseModel.evaluations),
        )
        .where(
            ExamResolutionModel.id == resolution_id,
            ExamResolutionModel.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_resolution_for_answer(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ExamResolutionModel | None:
    result = await db.execute(
        select(ExamResolutionModel)
        .options(
            selectinload(ExamResolutionModel.exam)
            .selectinload(ExamModel.questions)
            .selectinload(QuestionModel.options),
            selectinload(ExamResolutionModel.responses).selectinload(QuestionResponseModel.items),
            selectinload(ExamResolutionModel.responses).selectinload(QuestionResponseModel.evaluations),
        )
        .where(
            ExamResolutionModel.id == resolution_id,
            ExamResolutionModel.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_question_response_by_id(db: AsyncSession, response_id: UUID) -> QuestionResponseModel | None:
    result = await db.execute(
        select(QuestionResponseModel)
        .options(
            selectinload(QuestionResponseModel.items),
            selectinload(QuestionResponseModel.evaluations),
        )
        .where(QuestionResponseModel.id == response_id)
    )
    return result.scalar_one_or_none()


async def get_resolution_for_evaluation(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ExamResolutionModel | None:
    result = await db.execute(
        select(ExamResolutionModel)
        .options(
            selectinload(ExamResolutionModel.exam)
            .selectinload(ExamModel.questions)
            .selectinload(QuestionModel.options),
            selectinload(ExamResolutionModel.responses)
            .selectinload(QuestionResponseModel.items)
            .selectinload(QuestionResponseItemModel.option),
            selectinload(ExamResolutionModel.responses)
            .selectinload(QuestionResponseModel.question)
            .selectinload(QuestionModel.options),
            selectinload(ExamResolutionModel.responses).selectinload(QuestionResponseModel.evaluations),
        )
        .where(
            ExamResolutionModel.id == resolution_id,
            ExamResolutionModel.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_question_response_for_evaluation(db: AsyncSession, response_id: UUID) -> QuestionResponseModel | None:
    result = await db.execute(
        select(QuestionResponseModel)
        .options(
            selectinload(QuestionResponseModel.items),
            selectinload(QuestionResponseModel.evaluations),
        )
        .where(QuestionResponseModel.id == response_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


def add_resolution(db: AsyncSession, resolution: ExamResolutionModel) -> None:
    db.add(resolution)


async def add_response(db: AsyncSession, response: QuestionResponseModel) -> None:
    db.add(response)
    await db.flush()


async def clear_response_history(db: AsyncSession, response: QuestionResponseModel) -> None:
    for item in list(response.items):
        await db.delete(item)
    for evaluation in list(response.evaluations):
        await db.delete(evaluation)
    await db.flush()


def add_response_item(db: AsyncSession, item: QuestionResponseItemModel) -> None:
    db.add(item)


async def clear_response_evaluations(db: AsyncSession, response: QuestionResponseModel) -> None:
    for old_evaluation in list(response.evaluations):
        await db.delete(old_evaluation)
    await db.flush()
