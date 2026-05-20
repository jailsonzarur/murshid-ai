from __future__ import annotations

from datetime import UTC, datetime
from typing import overload
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.exams.models import ExamModel, ExamStatus
from src.features.files.services.bucket_service import get_bucket_service
from src.features.questions.models import QuestionModel, QuestionType
from src.features.resolutions.models import (
    ExamResolutionMode,
    ExamResolutionModel,
    ExamResolutionResult,
    ExamResolutionStatus,
    QuestionResponseItemModel,
    QuestionResponseModel,
)
from src.features.resolutions.schemas.resolution_schemas import (
    CreateResolutionSchema,
    QuestionResponseEvaluationSchema,
    QuestionResponseItemSchema,
    QuestionResponseSchema,
    ResolutionDetailSchema,
    ResolutionOptionSchema,
    ResolutionQuestionDetailSchema,
    ResolutionQuestionSchema,
    ResolutionSubmitSchema,
    ResolutionSummarySchema,
    ResponseItemInputSchema,
    UpsertQuestionResponseSchema,
)

ACTIVE_RESOLUTION_STATUSES = {
    ExamResolutionStatus.IN_PROGRESS,
    ExamResolutionStatus.PAUSED,
}
PASSING_SCORE = 0.7


async def get_active_resolution(
    db: AsyncSession,
    *,
    exam_id: UUID,
    user_id: UUID,
) -> ResolutionSummarySchema:
    resolution = await get_active_resolution_model(db, exam_id=exam_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Nenhuma resolução em andamento encontrada."], "data": None},
        )

    return ResolutionSummarySchema.model_validate(resolution)


async def list_exam_resolutions(
    db: AsyncSession,
    *,
    exam_id: UUID,
    user_id: UUID,
) -> list[ResolutionSummarySchema]:
    result = await db.execute(
        select(ExamResolutionModel)
        .where(
            ExamResolutionModel.exam_id == exam_id,
            ExamResolutionModel.user_id == user_id,
        )
        .order_by(ExamResolutionModel.created_at.desc())
    )

    return [ResolutionSummarySchema.model_validate(resolution) for resolution in result.scalars().all()]


async def create_exam_resolution(
    db: AsyncSession,
    *,
    exam_id: UUID,
    user_id: UUID,
    payload: CreateResolutionSchema,
) -> ResolutionSummarySchema:
    active_resolution = await get_active_resolution_model(db, exam_id=exam_id, user_id=user_id)
    if active_resolution is not None:
        return ResolutionSummarySchema.model_validate(active_resolution)

    exam = await get_exam_model_for_resolution(db, exam_id)
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Prova não encontrada."], "data": None},
        )

    if exam.status != ExamStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A prova ainda não está pronta para resolução."], "data": None},
        )

    if not exam.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A prova não possui questões para resolução."], "data": None},
        )

    now = datetime.now(UTC)
    resolution = ExamResolutionModel(
        exam_id=exam_id,
        user_id=user_id,
        mode=payload.mode,
        status=ExamResolutionStatus.IN_PROGRESS,
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(resolution)
    await db.commit()
    await db.refresh(resolution)

    return ResolutionSummarySchema.model_validate(resolution)


async def get_resolution_detail(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ResolutionDetailSchema:
    resolution = await get_resolution_model_for_detail(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Resolução não encontrada."], "data": None},
        )

    bucket_service = get_bucket_service()
    responses_by_question_id = {response.question_id: response for response in resolution.responses}
    questions = [
        ResolutionQuestionDetailSchema(
            question=ResolutionQuestionSchema(
                id=question.id,
                type=question.type.value,
                statement=question.statement,
                image_url=_get_viewer_image_url(bucket_service, question.image_url),
                explanation=question.explanation or question.justification,
                expected_answer=question.expected_answer,
                exam_order=question.exam_order,
                options=[
                    ResolutionOptionSchema(id=option.id, text=option.text, letter=option.letter)
                    for option in sorted(question.options, key=lambda item: item.letter or "")
                ],
            ),
            response=_serialize_response(responses_by_question_id.get(question.id)),
        )
        for question in sorted(resolution.exam.questions, key=lambda item: item.exam_order)
    ]

    return ResolutionDetailSchema(
        resolution=ResolutionSummarySchema.model_validate(resolution),
        questions=questions,
        can_show_evaluations=resolution.mode == ExamResolutionMode.STUDY
        or resolution.status == ExamResolutionStatus.GRADED,
    )


async def upsert_question_response(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    question_id: UUID,
    user_id: UUID,
    payload: UpsertQuestionResponseSchema,
) -> QuestionResponseSchema:
    resolution = await get_resolution_model_for_answer(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Resolução não encontrada."], "data": None},
        )

    if resolution.status != ExamResolutionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A resolução não está em andamento."], "data": None},
        )

    question = next((item for item in resolution.exam.questions if item.id == question_id), None)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Questão não encontrada nesta prova."], "data": None},
        )

    _validate_response_items(question, payload.items)

    response = next((item for item in resolution.responses if item.question_id == question_id), None)
    now = datetime.now(UTC)
    if response is None:
        response = QuestionResponseModel(
            resolution_id=resolution.id,
            question_id=question_id,
            answered_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(response)
        await db.flush()
    else:
        response.answered_at = now
        response.updated_at = now
        for item in list(response.items):
            await db.delete(item)
        for evaluation in list(response.evaluations):
            await db.delete(evaluation)
        await db.flush()

    for item in payload.items:
        db.add(
            QuestionResponseItemModel(
                response_id=response.id,
                option_id=item.option_id,
                text_answer=item.text_answer.strip() if item.text_answer else None,
                created_at=now,
                updated_at=now,
            )
        )

    await db.commit()

    refreshed_response = await get_question_response_model(db, response.id)
    if refreshed_response is None:
        raise RuntimeError(f"Question response was not found after save: {response.id}")

    return _serialize_response(refreshed_response)


async def pause_resolution(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ResolutionSummarySchema:
    resolution = await get_resolution_model(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Resolução não encontrada."], "data": None},
        )

    if resolution.status != ExamResolutionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A resolução não está em andamento."], "data": None},
        )

    now = datetime.now(UTC)
    resolution.time_spent_seconds += _elapsed_seconds(resolution.updated_at, now)
    resolution.paused_at = now
    resolution.status = ExamResolutionStatus.PAUSED
    resolution.updated_at = now
    await db.commit()
    await db.refresh(resolution)

    return ResolutionSummarySchema.model_validate(resolution)


async def resume_resolution(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ResolutionSummarySchema:
    resolution = await get_resolution_model(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Resolução não encontrada."], "data": None},
        )

    if resolution.status != ExamResolutionStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A resolução não está pausada."], "data": None},
        )

    now = datetime.now(UTC)
    resolution.paused_at = None
    resolution.status = ExamResolutionStatus.IN_PROGRESS
    resolution.updated_at = now
    await db.commit()
    await db.refresh(resolution)

    return ResolutionSummarySchema.model_validate(resolution)


async def submit_resolution(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ResolutionSubmitSchema:
    resolution = await get_resolution_model_for_submit(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Resolução não encontrada."], "data": None},
        )

    if resolution.status not in {ExamResolutionStatus.IN_PROGRESS, ExamResolutionStatus.PAUSED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A resolução não pode ser finalizada neste status."], "data": None},
        )

    now = datetime.now(UTC)
    if resolution.status == ExamResolutionStatus.IN_PROGRESS:
        resolution.time_spent_seconds += _elapsed_seconds(resolution.updated_at, now)

    resolution.paused_at = None
    resolution.status = ExamResolutionStatus.SUBMITTED
    resolution.submitted_at = now
    resolution.updated_at = now

    if resolution.mode == ExamResolutionMode.STUDY:
        question_count = len(resolution.exam.questions)
        total_score = sum(response.evaluations[0].score for response in resolution.responses if response.evaluations)
        resolution_score = total_score / question_count if question_count else 0
        resolution.score = resolution_score
        resolution.result = (
            ExamResolutionResult.PASSED if resolution_score >= PASSING_SCORE else ExamResolutionResult.FAILED
        )
        resolution.status = ExamResolutionStatus.GRADED
        resolution.graded_at = now

    await db.commit()
    await db.refresh(resolution)

    return ResolutionSubmitSchema(resolution=ResolutionSummarySchema.model_validate(resolution))


async def get_active_resolution_model(
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


async def get_exam_model_for_resolution(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .options(selectinload(ExamModel.questions).selectinload(QuestionModel.options))
        .where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def get_resolution_model(
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


async def get_resolution_model_for_submit(
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


async def get_resolution_model_for_detail(
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


async def get_resolution_model_for_answer(
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


async def get_question_response_model(db: AsyncSession, response_id: UUID) -> QuestionResponseModel | None:
    result = await db.execute(
        select(QuestionResponseModel)
        .options(
            selectinload(QuestionResponseModel.items),
            selectinload(QuestionResponseModel.evaluations),
        )
        .where(QuestionResponseModel.id == response_id)
    )
    return result.scalar_one_or_none()


def _validate_response_items(question: QuestionModel, items: list[ResponseItemInputSchema]) -> None:
    option_ids = {option.id for option in question.options}

    if question.type in {QuestionType.OBJECTIVE_SINGLE, QuestionType.OBJECTIVE_MULTI}:
        selected_option_ids: list[UUID] = []
        for item in items:
            if item.option_id is None:
                raise _invalid_response("Questões objetivas devem enviar option_id.")
            if item.text_answer:
                raise _invalid_response("Questões objetivas não aceitam resposta textual.")
            if item.option_id not in option_ids:
                raise _invalid_response("A alternativa selecionada não pertence à questão.")
            selected_option_ids.append(item.option_id)

        if len(selected_option_ids) != len(set(selected_option_ids)):
            raise _invalid_response("Alternativas duplicadas na resposta.")
        if question.type == QuestionType.OBJECTIVE_SINGLE and len(selected_option_ids) > 1:
            raise _invalid_response("Esta questão aceita apenas uma alternativa.")
        return

    if question.options:
        answered_option_ids: list[UUID] = []
        for item in items:
            if item.option_id is None:
                raise _invalid_response("Subitens subjetivos devem enviar option_id.")
            if item.option_id not in option_ids:
                raise _invalid_response("O subitem respondido não pertence à questão.")
            if not item.text_answer or not item.text_answer.strip():
                raise _invalid_response("Respostas subjetivas não podem estar vazias.")
            answered_option_ids.append(item.option_id)

        if len(answered_option_ids) != len(set(answered_option_ids)):
            raise _invalid_response("Subitens duplicados na resposta.")
        return

    if len(items) != 1:
        raise _invalid_response("Questões subjetivas sem subitens aceitam apenas uma resposta textual.")

    item = items[0]
    if item.option_id is not None:
        raise _invalid_response("Questões subjetivas sem subitens não aceitam option_id.")
    if not item.text_answer or not item.text_answer.strip():
        raise _invalid_response("Respostas subjetivas não podem estar vazias.")


def _invalid_response(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"success": False, "errors": [message], "data": None},
    )


@overload
def _serialize_response(response: QuestionResponseModel) -> QuestionResponseSchema: ...


@overload
def _serialize_response(response: None) -> None: ...


def _serialize_response(response: QuestionResponseModel | None) -> QuestionResponseSchema | None:
    if response is None:
        return None

    evaluation = response.evaluations[0] if response.evaluations else None
    return QuestionResponseSchema(
        id=response.id,
        question_id=response.question_id,
        answered_at=response.answered_at,
        items=[
            QuestionResponseItemSchema(
                id=item.id,
                option_id=item.option_id,
                text_answer=item.text_answer,
            )
            for item in response.items
        ],
        evaluation=QuestionResponseEvaluationSchema.model_validate(evaluation) if evaluation else None,
    )


def _get_viewer_image_url(bucket_service, image_url: str | None) -> str | None:
    if not image_url:
        return None

    if image_url.startswith("data:"):
        return image_url

    return bucket_service.get_presigned_url(image_url)


def _elapsed_seconds(start: datetime, end: datetime) -> int:
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)

    return max(0, round((end - start).total_seconds()))
