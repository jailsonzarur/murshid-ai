from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.categories.models import CategoryModel


async def get_category_by_name(db: AsyncSession, name: str) -> CategoryModel | None:
    result = await db.execute(select(CategoryModel).where(CategoryModel.name == name))
    return result.scalar_one_or_none()


async def get_category_by_id(db: AsyncSession, category_id: UUID) -> CategoryModel | None:
    return await db.get(CategoryModel, category_id)


async def list_categories(db: AsyncSession) -> list[CategoryModel]:
    result = await db.execute(select(CategoryModel).order_by(CategoryModel.name))
    return list(result.scalars().all())


def add_category(db: AsyncSession, category: CategoryModel) -> None:
    db.add(category)


async def delete_category(db: AsyncSession, category: CategoryModel) -> None:
    await db.delete(category)
