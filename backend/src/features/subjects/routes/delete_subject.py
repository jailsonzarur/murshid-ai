from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import DeleteSubjectResponse
from src.features.subjects.services.subject_service import remove_subject
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.delete(
    "/{subject_id}",
    operation_id="deleteSubject",
    response_model=SuccessResponse[DeleteSubjectResponse],
    responses={404: {"model": ErrorResponse}},
)
async def delete_subject_route(
    subject_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await remove_subject(db, subject_id, current_user.id)
    return SuccessResponse(
        success=True,
        errors=None,
        data=DeleteSubjectResponse(subject_id=subject_id, message="Matéria excluída com sucesso."),
    )
