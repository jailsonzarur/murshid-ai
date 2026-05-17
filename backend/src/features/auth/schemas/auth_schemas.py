import re
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.shared.enums.enums import UserRole


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if len(password) > 128:
        raise ValueError("A senha deve ter no máximo 128 caracteres.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("A senha deve conter pelo menos uma letra maiúscula.")
    if not re.search(r"[a-z]", password):
        raise ValueError("A senha deve conter pelo menos uma letra minúscula.")
    if not re.search(r"\d", password):
        raise ValueError("A senha deve conter pelo menos um número.")
    return password


class SignUpSchema(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class SignInSchema(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=6)]


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserSchema(BaseModel):
    name: str
    email: EmailStr
    role: UserRole
