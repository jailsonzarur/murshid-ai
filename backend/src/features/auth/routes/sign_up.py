from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.schemas.auth_schemas import SignUpSchema
from src.features.auth.services.auth_service import register_user
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/sign-up",
    operation_id="signUp",
    status_code=201,
    response_model=SuccessResponse[None],
    responses={409: {"model": ErrorResponse}},
)
async def sign_up(request: SignUpSchema, db: Annotated[AsyncSession, Depends(get_db)]):
    await register_user(db, request.name, request.email, request.password)
    return SuccessResponse[None](success=True, errors=None, data=None)
