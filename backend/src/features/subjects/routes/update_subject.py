from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import SubjectSchema, UpdateSubjectSchema
from src.features.subjects.services.subject_service import update_subject
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.patch(
    "/{subject_id}",
    operation_id="updateSubject",
    response_model=SuccessResponse[SubjectSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_subject_route(
    subject_id: UUID,
    payload: UpdateSubjectSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subject = await update_subject(db, subject_id=subject_id, user_id=current_user.id, payload=payload)
    return SuccessResponse(success=True, errors=None, data=subject)
