from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.resolutions.schemas.resolution_schemas import ResolutionSummarySchema
from src.features.resolutions.services.resolution_service import list_exam_resolutions
from src.shared.schemas.http import SuccessResponse
from src.features.auth.utils import CurrentUser, get_current_user

router = APIRouter()


@router.get(
    "/{exam_id}/resolutions",
    operation_id="getExamResolutions",
    response_model=SuccessResponse[list[ResolutionSummarySchema]],
)
async def get_exam_resolutions_route(
    exam_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    resolutions = await list_exam_resolutions(db, exam_id=exam_id, user_id=current_user.id)
    return SuccessResponse(success=True, errors=None, data=resolutions)
