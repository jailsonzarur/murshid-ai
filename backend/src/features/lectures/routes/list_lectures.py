from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import LectureSummarySchema
from src.features.lectures.services.lecture_service import list_user_lectures
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.get(
    "",
    operation_id="listLectures",
    response_model=SuccessResponse[list[LectureSummarySchema]],
)
async def list_lectures_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    lectures = await list_user_lectures(db, user_id=current_user.id)
    return SuccessResponse(success=True, errors=None, data=lectures)
