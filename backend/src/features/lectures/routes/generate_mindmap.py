from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.services.lecture_service import request_mindmap
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/{lecture_id}/mindmap",
    operation_id="generateLectureMindmap",
    status_code=202,
    response_model=SuccessResponse[None],
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def generate_mindmap_route(
    lecture_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await request_mindmap(db, lecture_id, current_user.id)
    return SuccessResponse[None](success=True, errors=None, data=None)
