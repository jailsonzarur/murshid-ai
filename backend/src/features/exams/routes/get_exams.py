from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.exams.schemas.exam_schemas import ExamListSchema
from src.features.exams.services.exam_service import list_exams
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.get("", operation_id="getExams", response_model=SuccessResponse[list[ExamListSchema]])
async def get_exams(db: Annotated[AsyncSession, Depends(get_db)]):
    exams = await list_exams(db)
    return SuccessResponse(success=True, errors=None, data=exams)
