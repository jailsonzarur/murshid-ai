from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.exams.schemas.exam_schemas import ExamViewerQuestionSchema
from src.features.exams.services.exam_service import list_exam_questions
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/{exam_id}/questions",
    operation_id="getExamQuestions",
    response_model=SuccessResponse[list[ExamViewerQuestionSchema]],
    responses={404: {"model": ErrorResponse}},
)
async def get_exam_questions(
    exam_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    questions = await list_exam_questions(db, exam_id)
    return SuccessResponse(success=True, errors=None, data=questions)
