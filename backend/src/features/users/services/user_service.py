from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.auth.utils import hash_password
from src.features.users.models import UserModel
from src.features.users.repository import (
    add_user,
    get_user_by_id,
    list_all_users,
    remove_user,
    user_exists_by_email,
)
from src.features.users.schemas.user_schemas import (
    CreateUserSchema,
    UpdateUserRoleSchema,
    UpdateUserSchema,
    UserListSchema,
)


async def list_users(db: AsyncSession) -> list[UserListSchema]:
    users = await list_all_users(db)
    return [UserListSchema.model_validate(user) for user in users]


async def create_user(db: AsyncSession, data: CreateUserSchema) -> None:
    if await user_exists_by_email(db, data.email):
        raise HTTPException(
            status_code=409,
            detail={"success": False, "errors": ["Um usuário com este e-mail já existe."], "data": None},
        )

    user = UserModel(name=data.name, email=data.email.lower(), password=hash_password(data.password), role=data.role)
    add_user(db, user)
    await db.commit()


async def create_user_with_hashed_password(
    db: AsyncSession,
    name: str,
    email: str,
    hashed_password: str,
) -> UserModel:
    user = UserModel(name=name, email=email.lower(), password=hashed_password)
    add_user(db, user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: UUID, data: UpdateUserSchema) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "errors": ["Usuário não encontrado."], "data": None},
        )

    if data.email is not None and data.email.lower() != user.email:
        if await user_exists_by_email(db, data.email, exclude_id=user_id):
            raise HTTPException(
                status_code=409,
                detail={"success": False, "errors": ["Usuário com este e-mail já existe."], "data": None},
            )
        user.email = data.email.lower()
    if data.name is not None:
        user.name = data.name
    if data.password is not None:
        user.password = hash_password(data.password)
    if data.role is not None:
        user.role = data.role

    await db.commit()


async def update_role(db: AsyncSession, user_id: UUID, data: UpdateUserRoleSchema) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "errors": ["Usuário não encontrado."], "data": None},
        )
    user.role = data.role
    await db.commit()


async def delete_user(db: AsyncSession, user_id: UUID, current_user_id: UUID) -> None:
    if current_user_id == user_id:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "errors": ["Não é possível excluir a si mesmo."], "data": None},
        )

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "errors": ["Usuário não encontrado."], "data": None},
        )

    await remove_user(db, user)
    await db.commit()
