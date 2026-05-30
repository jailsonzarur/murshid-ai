from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.users.services.user_service import delete_user
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.delete(
    "/{user_id}",
    operation_id="deleteUser",
    response_model=SuccessResponse[None],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def delete_user_route(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    await delete_user(db, user_id, current_user.id)
    return SuccessResponse[None](success=True, errors=None, data=None)
