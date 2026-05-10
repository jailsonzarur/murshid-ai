from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from decouple import config
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from starlette.requests import Request

SECRET_KEY: str = str(config("SECRET_KEY", default="change-me"))
ALGORITHM: str = str(config("ALGORITHM", default="HS256"))
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(str(config("ACCESS_TOKEN_EXPIRE_MINUTES", default="60")))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(str(config("REFRESH_TOKEN_EXPIRE_DAYS", default="7")))

security = HTTPBearer()


@dataclass
class CurrentUser:
    id: UUID
    role: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except (TypeError, ValueError):
        return False


def _create_token(data: dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(UTC) + expires_delta, "type": token_type})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict[str, Any]) -> str:
    return _create_token(data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: UUID, role: str) -> str:
    return _create_token({"sub": str(user_id), "role": role}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado",
        )

    if payload.get("type") != "refresh" or payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado",
        )
    return payload


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") not in (None, "access"):
            raise InvalidTokenError()
        user_id = payload.get("sub")
        role = payload.get("role", "GUEST")
        if user_id is None:
            raise InvalidTokenError()
        return CurrentUser(id=UUID(str(user_id)), role=role)
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except (InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")


def get_user_from_request(request: Request) -> CurrentUser | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    payload = decode_token(token)
    if payload.get("type") not in (None, "access"):
        return None
    user_id = payload.get("sub")
    role = payload.get("role", "GUEST")
    if user_id is None:
        return None
    return CurrentUser(id=UUID(str(user_id)), role=role)
