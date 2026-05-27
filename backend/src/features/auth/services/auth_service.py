from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.auth.utils import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> dict[str, str]:
    from src.features.users.services.user_service import get_user_model_by_email

    user = await get_user_model_by_email(db, email.lower())
    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=400,
            detail={"success": False, "errors": ["E-mail ou senha incorretos."], "data": None},
        )

    return {
        "access_token": create_access_token({"sub": str(user.id), "role": user.role.value}),
        "refresh_token": create_refresh_token(user.id, user.role.value),
        "token_type": "bearer",
    }


async def refresh_tokens(refresh_token: str) -> dict[str, str]:
    payload = decode_refresh_token(refresh_token)
    user_id = UUID(str(payload["sub"]))
    role = str(payload.get("role", "GUEST"))
    return {
        "access_token": create_access_token({"sub": str(user_id), "role": role}),
        "refresh_token": create_refresh_token(user_id, role),
        "token_type": "bearer",
    }


async def logout_user(refresh_token: str) -> None:
    return None


async def register_user(db: AsyncSession, name: str, email: str, password: str) -> None:
    from src.features.users.services.user_service import create_user_with_hashed_password, get_user_model_by_email

    existing = await get_user_model_by_email(db, email.lower())
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"success": False, "errors": ["E-mail já cadastrado."], "data": None},
        )

    await create_user_with_hashed_password(db, name, email.lower(), hash_password(password))


async def get_user_profile(db: AsyncSession, user_id: UUID) -> dict:
    from src.features.users.services.user_service import get_user_model_by_id

    user = await get_user_model_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "errors": ["Usuário não encontrado."], "data": None},
        )
    return {"name": user.name, "email": user.email, "role": user.role}
