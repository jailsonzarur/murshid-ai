from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.exams.schemas.exam_schemas import ExamDeleteResponse
from src.features.exams.services.exam_service import delete_exam
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.delete(
    "/{exam_id}",
    operation_id="deleteExam",
    response_model=SuccessResponse[ExamDeleteResponse],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def delete_exam_route(
    exam_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_exam(db, exam_id)

    return SuccessResponse(
        success=True,
        errors=None,
        data=ExamDeleteResponse(exam_id=exam_id, message="Prova excluída com sucesso."),
    )
