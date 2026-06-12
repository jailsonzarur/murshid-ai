from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import LectureSummarySchema
from src.features.lectures.services.lecture_service import pause_lecture
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/{lecture_id}/pause",
    operation_id="pauseLecture",
    response_model=SuccessResponse[LectureSummarySchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def pause_lecture_route(
    lecture_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    lecture = await pause_lecture(db, lecture_id=lecture_id, user_id=current_user.id)
    return SuccessResponse(success=True, errors=None, data=lecture)
