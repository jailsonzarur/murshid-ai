from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import (
    LectureDetailSchema,
    UpdateLectureSubjectSchema,
)
from src.features.lectures.services.lecture_service import change_lecture_subject
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.patch(
    "/{lecture_id}/subject",
    operation_id="updateLectureSubject",
    response_model=SuccessResponse[LectureDetailSchema],
    responses={404: {"model": ErrorResponse}},
)
async def update_lecture_subject_route(
    lecture_id: UUID,
    payload: UpdateLectureSubjectSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    lecture = await change_lecture_subject(
        db, lecture_id=lecture_id, user_id=current_user.id, subject_id=payload.subject_id
    )
    return SuccessResponse(success=True, errors=None, data=lecture)
