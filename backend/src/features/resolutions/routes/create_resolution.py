from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.resolutions.schemas.resolution_schemas import CreateResolutionSchema, ResolutionSummarySchema
from src.features.resolutions.services.resolution_service import create_exam_resolution
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/{exam_id}/resolutions",
    operation_id="createExamResolution",
    status_code=201,
    response_model=SuccessResponse[ResolutionSummarySchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def create_resolution_route(
    exam_id: UUID,
    payload: CreateResolutionSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    resolution = await create_exam_resolution(db, exam_id=exam_id, user_id=current_user.id, payload=payload)
    return SuccessResponse(success=True, errors=None, data=resolution)
