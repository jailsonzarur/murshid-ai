from fastapi import APIRouter

from src.features.auth.schemas.auth_schemas import RefreshTokenRequest, TokenPairResponse
from src.features.auth.services.auth_service import refresh_tokens
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.post("/refresh", operation_id="refreshTokens", response_model=SuccessResponse[TokenPairResponse])
async def refresh(body: RefreshTokenRequest):
    token_data = await refresh_tokens(body.refresh_token)
    return SuccessResponse(success=True, errors=None, data=TokenPairResponse(**token_data))
