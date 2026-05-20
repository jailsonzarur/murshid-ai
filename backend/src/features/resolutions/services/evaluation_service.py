from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.exams.models import ExamModel
from src.features.questions.models import QuestionModel
from src.features.questions.services.question_evaluation_service import (
    EvaluationOption,
    UserAnswerItem,
    evaluate_user_response,
)
from src.features.resolutions.models import (
    ExamResolutionMode,
    ExamResolutionModel,
    ExamResolutionResult,
    ExamResolutionStatus,
    QuestionResponseEvaluationModel,
    QuestionResponseItemModel,
    QuestionResponseModel,
    ResponseEvaluationSource,
)
from src.features.resolutions.schemas.resolution_schemas import (
    QuestionResponseSchema,
    ResolutionSummarySchema,
)
from src.features.resolutions.services.resolution_service import _elapsed_seconds, _serialize_response

PASSING_SCORE = 0.7
MAX_PARALLEL_EVALUATIONS = 5


@dataclass(frozen=True)
class EvaluationOutput:
    score: float
    feedback: str
    evaluation_source: ResponseEvaluationSource
    model_name: str | None = None
    raw_output: str | None = None


async def evaluate_resolution_question(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    question_id: UUID,
    user_id: UUID,
) -> QuestionResponseSchema:
    resolution = await get_resolution_model_for_evaluation(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Resolução não encontrada."], "data": None},
        )

    if resolution.mode != ExamResolutionMode.STUDY or resolution.status != ExamResolutionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "errors": ["Correção por questão só está disponível no modo estudo em andamento."],
                "data": None,
            },
        )

    response = next((item for item in resolution.responses if item.question_id == question_id), None)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A questão ainda não foi respondida."], "data": None},
        )

    output = await evaluate_response(response)
    await persist_response_evaluation(db, response, output)
    await db.commit()

    refreshed_response = await get_question_response_model_for_evaluation(db, response.id)
    if refreshed_response is None:
        raise RuntimeError(f"Question response was not found after evaluation: {response.id}")

    return _serialize_response(refreshed_response)


async def enqueue_resolution_evaluation(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> tuple[str, ResolutionSummarySchema]:
    resolution = await get_resolution_model_for_evaluation(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Resolução não encontrada."], "data": None},
        )

    if resolution.status not in {
        ExamResolutionStatus.IN_PROGRESS,
        ExamResolutionStatus.PAUSED,
        ExamResolutionStatus.SUBMITTED,
        ExamResolutionStatus.GRADED,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A resolução não pode ser corrigida neste status."], "data": None},
        )

    if not resolution.responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["A resolução não possui respostas para corrigir."], "data": None},
        )

    now = datetime.now(UTC)
    if resolution.status == ExamResolutionStatus.IN_PROGRESS:
        resolution.time_spent_seconds += _elapsed_seconds(resolution.updated_at, now)

    resolution.status = ExamResolutionStatus.SUBMITTED
    resolution.result = None
    resolution.score = None
    resolution.paused_at = None
    resolution.submitted_at = resolution.submitted_at or now
    resolution.graded_at = None
    resolution.updated_at = now
    await db.commit()
    await db.refresh(resolution)

    from src.features.resolutions.tasks import evaluate_resolution_task

    task = cast(Any, evaluate_resolution_task).delay(str(resolution.id), str(user_id))
    return str(task.id), ResolutionSummarySchema.model_validate(resolution)


async def evaluate_resolution_responses(
    db: AsyncSession,
    *,
    resolution_id: UUID,
    user_id: UUID,
) -> ResolutionSummarySchema:
    resolution = await get_resolution_model_for_evaluation(db, resolution_id=resolution_id, user_id=user_id)
    if resolution is None:
        raise RuntimeError(f"Resolution was not found for evaluation: {resolution_id}")

    if resolution.status not in {ExamResolutionStatus.SUBMITTED, ExamResolutionStatus.GRADED}:
        raise RuntimeError(f"Resolution cannot be evaluated in status {resolution.status}")

    now = datetime.now(UTC)
    if not resolution.exam.questions:
        resolution.status = ExamResolutionStatus.ERROR
        resolution.updated_at = now
        await db.commit()
        return ResolutionSummarySchema.model_validate(resolution)

    try:
        semaphore = asyncio.Semaphore(MAX_PARALLEL_EVALUATIONS)

        async def evaluate_with_limit(
            response: QuestionResponseModel,
        ) -> tuple[QuestionResponseModel, EvaluationOutput]:
            async with semaphore:
                return response, await evaluate_response(response)

        evaluated_responses = await asyncio.gather(
            *(evaluate_with_limit(response) for response in resolution.responses),
        )

        total_score = 0.0
        for response, output in evaluated_responses:
            await persist_response_evaluation(db, response, output)
            total_score += output.score

        question_count = len(resolution.exam.questions)
        resolution_score = total_score / question_count
        resolution.score = resolution_score
        resolution.result = (
            ExamResolutionResult.PASSED if resolution_score >= PASSING_SCORE else ExamResolutionResult.FAILED
        )
        resolution.status = ExamResolutionStatus.GRADED
        graded_at = datetime.now(UTC)
        resolution.graded_at = graded_at
        resolution.updated_at = graded_at
        await db.commit()
        await db.refresh(resolution)
        return ResolutionSummarySchema.model_validate(resolution)
    except Exception:
        resolution.status = ExamResolutionStatus.ERROR
        resolution.updated_at = datetime.now(UTC)
        await db.commit()
        raise


async def evaluate_response(response: QuestionResponseModel) -> EvaluationOutput:
    if response.evaluations:
        evaluation = response.evaluations[0]
        return EvaluationOutput(
            score=evaluation.score,
            feedback=evaluation.feedback or "",
            evaluation_source=evaluation.evaluation_source,
            model_name=evaluation.model_name,
            raw_output=evaluation.raw_output,
        )

    evaluated = await evaluate_user_response(
        question_type=response.question.type.value,
        statement=response.question.statement,
        options=[
            EvaluationOption(
                key=str(option.id),
                letter=option.letter,
                text=option.text,
                is_correct=option.is_correct,
            )
            for option in sorted(response.question.options, key=lambda item: item.letter or "")
        ],
        student_answer=[
            UserAnswerItem(
                text_answer=item.text_answer,
                option_key=str(item.option_id) if item.option_id else None,
                option_letter=item.option.letter if item.option else None,
                option_text=item.option.text if item.option else None,
            )
            for item in response.items
        ],
        expected_answer=response.question.expected_answer,
        explanation=response.question.explanation or response.question.justification,
    )

    return EvaluationOutput(
        score=evaluated.score,
        feedback=evaluated.feedback,
        evaluation_source=ResponseEvaluationSource(evaluated.evaluation_source),
        model_name=evaluated.model_name,
        raw_output=evaluated.raw_output,
    )


async def persist_response_evaluation(
    db: AsyncSession,
    response: QuestionResponseModel,
    output: EvaluationOutput,
) -> None:
    for evaluation in list(response.evaluations):
        await db.delete(evaluation)

    await db.flush()
    now = datetime.now(UTC)
    db.add(
        QuestionResponseEvaluationModel(
            response_id=response.id,
            score=output.score,
            feedback=output.feedback,
            evaluation_source=output.evaluation_source,
            evaluated_at=now,
            model_name=output.model_name,
            raw_output=output.raw_output,
        )
    )

async def get_resolution_model_for_evaluation(
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


async def get_question_response_model_for_evaluation(
    db: AsyncSession,
    response_id: UUID,
) -> QuestionResponseModel | None:
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
