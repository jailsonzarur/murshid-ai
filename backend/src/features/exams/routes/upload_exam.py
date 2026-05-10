from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.exams.schemas.exam_schemas import ExamUploadResponse
from src.features.exams.services.exam_service import create_exam_and_dispatch_task
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/upload",
    operation_id="uploadExam",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SuccessResponse[ExamUploadResponse],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def upload_exam(
    name: Annotated[str, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    general_subject: Annotated[str | None, Form()] = None,
):
    exam = await create_exam_and_dispatch_task(db, name, general_subject, files)

    return SuccessResponse(
        success=True,
        errors=None,
        data=ExamUploadResponse(exam_id=exam.id, message="Exam upload accepted for processing"),
    )
