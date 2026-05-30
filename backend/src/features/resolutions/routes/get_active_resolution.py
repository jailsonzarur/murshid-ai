from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.resolutions.schemas.resolution_schemas import ResolutionSummarySchema
from src.features.resolutions.services.resolution_service import get_active_resolution
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/{exam_id}/resolutions/active",
    operation_id="getActiveExamResolution",
    response_model=SuccessResponse[ResolutionSummarySchema],
    responses={404: {"model": ErrorResponse}},
)
async def get_active_resolution_route(
    exam_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    resolution = await get_active_resolution(db, exam_id=exam_id, user_id=current_user.id)
    return SuccessResponse(success=True, errors=None, data=resolution)
