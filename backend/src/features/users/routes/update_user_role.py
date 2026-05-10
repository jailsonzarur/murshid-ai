from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.users.schemas.user_schemas import UpdateUserRoleSchema
from src.features.users.services.user_service import update_role
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.patch(
    "/{user_id}/role",
    operation_id="updateUserRole",
    response_model=SuccessResponse[None],
    responses={404: {"model": ErrorResponse}},
)
async def update_user_role(user_id: UUID, request: UpdateUserRoleSchema, db: Annotated[AsyncSession, Depends(get_db)]):
    await update_role(db, user_id, request)
    return SuccessResponse[None](success=True, errors=None, data=None)
