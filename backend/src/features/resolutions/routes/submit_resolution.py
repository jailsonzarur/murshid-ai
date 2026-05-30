from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.resolutions.schemas.resolution_schemas import ResolutionSubmitSchema
from src.features.resolutions.services.resolution_service import submit_resolution
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/{resolution_id}/submit",
    operation_id="submitResolution",
    response_model=SuccessResponse[ResolutionSubmitSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def submit_resolution_route(
    resolution_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    resolution = await submit_resolution(db, resolution_id=resolution_id, user_id=current_user.id)
    return SuccessResponse(success=True, errors=None, data=resolution)
