from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.resolutions.schemas.resolution_schemas import QuestionResponseSchema
from src.features.resolutions.services.evaluation_service import evaluate_resolution_question
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/{resolution_id}/questions/{question_id}/evaluate",
    operation_id="evaluateResolutionQuestion",
    response_model=SuccessResponse[QuestionResponseSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def evaluate_question_response_route(
    resolution_id: UUID,
    question_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    response = await evaluate_resolution_question(
        db,
        resolution_id=resolution_id,
        question_id=question_id,
        user_id=current_user.id,
    )
    return SuccessResponse(success=True, errors=None, data=response)
