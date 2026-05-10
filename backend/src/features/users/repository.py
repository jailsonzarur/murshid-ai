from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.users.models import UserModel


async def get_all_users(db: AsyncSession) -> list[UserModel]:
    result = await db.execute(select(UserModel).order_by(UserModel.name))
    return list(result.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.email == email.lower()))
    return result.scalar_one_or_none()


async def user_exists_by_email(db: AsyncSession, email: str, exclude_id: UUID | None = None) -> bool:
    stmt = select(UserModel).where(UserModel.email == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(UserModel.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_user_record(db: AsyncSession, user: UserModel) -> None:
    db.add(user)
    await db.commit()


async def delete_user_record(db: AsyncSession, user: UserModel) -> None:
    await db.delete(user)
    await db.commit()
