from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.resolutions.schemas.resolution_schemas import ResolutionDetailSchema
from src.features.resolutions.services.resolution_service import get_resolution_detail
from src.shared.schemas.http import ErrorResponse, SuccessResponse
from src.shared.utils.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get(
    "/{resolution_id}",
    operation_id="getResolution",
    response_model=SuccessResponse[ResolutionDetailSchema],
    responses={404: {"model": ErrorResponse}},
)
async def get_resolution_route(
    resolution_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    resolution = await get_resolution_detail(db, resolution_id=resolution_id, user_id=current_user.id)
    return SuccessResponse(success=True, errors=None, data=resolution)
