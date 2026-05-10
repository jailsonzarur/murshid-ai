from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.users.schemas.user_schemas import UpdateUserSchema
from src.features.users.services.user_service import update_user
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.put(
    "/{user_id}",
    operation_id="updateUser",
    response_model=SuccessResponse[None],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_user_route(user_id: UUID, request: UpdateUserSchema, db: Annotated[AsyncSession, Depends(get_db)]):
    await update_user(db, user_id, request)
    return SuccessResponse[None](success=True, errors=None, data=None)
