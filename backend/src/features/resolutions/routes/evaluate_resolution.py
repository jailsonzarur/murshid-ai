from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.resolutions.schemas.resolution_schemas import ResolutionEvaluationTaskSchema
from src.features.resolutions.services.evaluation_service import enqueue_resolution_evaluation
from src.shared.schemas.http import ErrorResponse, SuccessResponse
from src.features.auth.utils import CurrentUser, get_current_user

router = APIRouter()


@router.post(
    "/{resolution_id}/evaluate",
    operation_id="evaluateResolution",
    response_model=SuccessResponse[ResolutionEvaluationTaskSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    status_code=status.HTTP_202_ACCEPTED,
)
async def evaluate_resolution_route(
    resolution_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task_id, resolution = await enqueue_resolution_evaluation(db, resolution_id=resolution_id, user_id=current_user.id)
    return SuccessResponse(
        success=True,
        errors=None,
        data=ResolutionEvaluationTaskSchema(task_id=task_id, resolution=resolution),
    )
