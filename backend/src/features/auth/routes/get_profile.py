from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.schemas.auth_schemas import UserSchema
from src.features.auth.services.auth_service import get_user_profile
from src.shared.schemas.http import ErrorResponse, SuccessResponse
from src.features.auth.utils import CurrentUser, get_current_user

router = APIRouter()


@router.get(
    "/profile",
    operation_id="getProfile",
    response_model=SuccessResponse[UserSchema],
    responses={401: {"model": ErrorResponse}},
)
async def get_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    profile = await get_user_profile(db, current_user.id)
    return SuccessResponse(success=True, errors=None, data=UserSchema(**profile))
