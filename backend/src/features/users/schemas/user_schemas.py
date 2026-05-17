from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.features.auth.schemas.auth_schemas import validate_password_strength
from src.shared.enums.enums import UserRole


class UserListSchema(BaseModel):
    id: Annotated[UUID, Field(description="ID do usuário")]
    name: Annotated[str, Field(description="Nome do usuário")]
    email: Annotated[EmailStr, Field(description="E-mail do usuário")]
    role: Annotated[UserRole, Field(description="Papel do usuário")]
    created_at: Annotated[datetime, Field(description="Data de criação")]
    updated_at: Annotated[datetime, Field(description="Data de atualização")]

    model_config = ConfigDict(from_attributes=True)


class CreateUserSchema(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    role: UserRole = UserRole.GUEST

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UpdateUserSchema(BaseModel):
    name: Annotated[str | None, Field(min_length=2, max_length=100)] = None
    email: EmailStr | None = None
    password: Annotated[str | None, Field(min_length=8, max_length=128)] = None
    role: UserRole | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str | None) -> str | None:
        return validate_password_strength(value) if value is not None else value


class UpdateUserRoleSchema(BaseModel):
    role: UserRole
