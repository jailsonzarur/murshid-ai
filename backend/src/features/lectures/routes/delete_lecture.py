from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.services.lecture_service import remove_lecture
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


class DeleteLectureResponse(BaseModel):
    lecture_id: UUID
    message: str


@router.delete(
    "/{lecture_id}",
    operation_id="deleteLecture",
    response_model=SuccessResponse[DeleteLectureResponse],
    responses={404: {"model": ErrorResponse}},
)
async def delete_lecture_route(
    lecture_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await remove_lecture(db, lecture_id=lecture_id, user_id=current_user.id)
    return SuccessResponse(
        success=True,
        errors=None,
        data=DeleteLectureResponse(lecture_id=lecture_id, message="Aula excluída com sucesso."),
    )
