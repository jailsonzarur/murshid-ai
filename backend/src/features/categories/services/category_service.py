from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.categories.models import CategoryModel


async def get_or_create_category(
    db: AsyncSession,
    category_cache: dict[str, CategoryModel],
    category_name: str,
) -> CategoryModel:
    normalized_name = " ".join(category_name.strip().split())
    normalized_name = (normalized_name or "Uncategorized")[:100]

    if normalized_name in category_cache:
        return category_cache[normalized_name]

    result = await db.execute(select(CategoryModel).where(CategoryModel.name == normalized_name))
    category = result.scalar_one_or_none()

    if category is None:
        category = CategoryModel(name=normalized_name)
        db.add(category)
        await db.flush()

    category_cache[normalized_name] = category
    return category
