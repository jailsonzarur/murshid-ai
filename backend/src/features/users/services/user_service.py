from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal
from src.features.users.models import UserModel
from src.features.users.schemas.user_schemas import (
    CreateUserSchema,
    UpdateUserRoleSchema,
    UpdateUserSchema,
    UserListSchema,
)
from src.features.auth.utils import hash_password


async def list_users(db: AsyncSession) -> list[UserListSchema]:
    users = await get_all_user_models(db)
    return [UserListSchema.model_validate(user) for user in users]


async def create_user(db: AsyncSession, data: CreateUserSchema) -> None:
    if await user_exists_by_email(db, data.email):
        raise HTTPException(
            status_code=409,
            detail={"success": False, "errors": ["Um usuário com este e-mail já existe."], "data": None},
        )

    user = UserModel(name=data.name, email=data.email.lower(), password=hash_password(data.password), role=data.role)
    db.add(user)
    await db.commit()


async def create_user_with_hashed_password(
    db: AsyncSession,
    name: str,
    email: str,
    hashed_password: str,
) -> UserModel:
    user = UserModel(name=name, email=email.lower(), password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: UUID, data: UpdateUserSchema) -> None:
    user = await get_user_model_by_id(db, user_id)
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
    user = await get_user_model_by_id(db, user_id)
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

    user = await get_user_model_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "errors": ["Usuário não encontrado."], "data": None},
        )

    await db.delete(user)
    await db.commit()


async def get_user_model_by_id(db: AsyncSession, user_id: UUID) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def get_user_model_by_id_from_new_session(user_id: UUID, session_factory=AsyncSessionLocal) -> UserModel | None:
    async with session_factory() as db:
        return await get_user_model_by_id(db, user_id)


async def get_all_user_models(db: AsyncSession) -> list[UserModel]:
    result = await db.execute(select(UserModel).order_by(UserModel.name))
    return list(result.scalars().all())


async def get_user_model_by_email(db: AsyncSession, email: str) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.email == email.lower()))
    return result.scalar_one_or_none()


async def user_exists_by_email(db: AsyncSession, email: str, exclude_id: UUID | None = None) -> bool:
    stmt = select(UserModel).where(UserModel.email == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(UserModel.id != exclude_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
