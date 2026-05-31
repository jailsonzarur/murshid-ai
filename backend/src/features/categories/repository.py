from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.categories.models import CategoryModel


async def get_category_by_name(db: AsyncSession, name: str) -> CategoryModel | None:
    result = await db.execute(select(CategoryModel).where(CategoryModel.name == name))
    return result.scalar_one_or_none()


def add_category(db: AsyncSession, category: CategoryModel) -> None:
    db.add(category)
