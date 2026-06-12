from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import LectureDetailSchema
from src.features.lectures.services.lecture_service import get_lecture_detail
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/{lecture_id}",
    operation_id="getLecture",
    response_model=SuccessResponse[LectureDetailSchema],
    responses={404: {"model": ErrorResponse}},
)
async def get_lecture_route(
    lecture_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    lecture = await get_lecture_detail(db, lecture_id=lecture_id, user_id=current_user.id)
    return SuccessResponse(success=True, errors=None, data=lecture)
