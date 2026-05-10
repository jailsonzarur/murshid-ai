from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.schemas.auth_schemas import SignInSchema, TokenPairResponse
from src.features.auth.services.auth_service import authenticate_user
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/sign-in",
    operation_id="signIn",
    response_model=SuccessResponse[TokenPairResponse],
    responses={400: {"model": ErrorResponse}},
)
async def sign_in(body: SignInSchema, db: Annotated[AsyncSession, Depends(get_db)]):
    token_data = await authenticate_user(db, body.email, body.password)
    return SuccessResponse(success=True, errors=None, data=TokenPairResponse(**token_data))
