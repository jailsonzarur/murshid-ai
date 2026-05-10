from fastapi import APIRouter

from src.features.auth.schemas.auth_schemas import RefreshTokenRequest
from src.features.auth.services.auth_service import logout_user
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.post("/logout", operation_id="logout", response_model=SuccessResponse[None])
async def logout(body: RefreshTokenRequest):
    await logout_user(body.refresh_token)
    return SuccessResponse[None](success=True, errors=None, data=None)
