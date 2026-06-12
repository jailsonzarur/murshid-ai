from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import LectureSummarySchema, StartLectureSchema
from src.features.lectures.services.lecture_service import start_lecture
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "",
    operation_id="startLecture",
    status_code=201,
    response_model=SuccessResponse[LectureSummarySchema],
    responses={400: {"model": ErrorResponse}},
)
async def start_lecture_route(
    payload: StartLectureSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    lecture = await start_lecture(db, user_id=current_user.id, payload=payload)
    return SuccessResponse(success=True, errors=None, data=lecture)
