from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.resolutions.schemas.resolution_schemas import QuestionResponseSchema, UpsertQuestionResponseSchema
from src.features.resolutions.services.resolution_service import upsert_question_response
from src.shared.schemas.http import ErrorResponse, SuccessResponse
from src.shared.utils.auth import CurrentUser, get_current_user

router = APIRouter()


@router.put(
    "/{resolution_id}/questions/{question_id}/response",
    operation_id="upsertResolutionQuestionResponse",
    response_model=SuccessResponse[QuestionResponseSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def upsert_question_response_route(
    resolution_id: UUID,
    question_id: UUID,
    payload: UpsertQuestionResponseSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    response = await upsert_question_response(
        db,
        resolution_id=resolution_id,
        question_id=question_id,
        user_id=current_user.id,
        payload=payload,
    )
    return SuccessResponse(success=True, errors=None, data=response)
