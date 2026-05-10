from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.users.schemas.user_schemas import CreateUserSchema
from src.features.users.services.user_service import create_user
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/",
    operation_id="createUser",
    status_code=201,
    response_model=SuccessResponse[None],
    responses={409: {"model": ErrorResponse}},
)
async def create_user_route(request: CreateUserSchema, db: Annotated[AsyncSession, Depends(get_db)]):
    await create_user(db, request)
    return SuccessResponse[None](success=True, errors=None, data=None)
