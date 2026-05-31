from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.features.categories.models import CategoryModel
from src.features.categories.repository import add_category, get_category_by_name


async def get_or_create_category(
    db: AsyncSession,
    category_cache: dict[str, CategoryModel],
    category_name: str,
) -> CategoryModel:
    normalized_name = " ".join(category_name.strip().split())
    normalized_name = (normalized_name or "Uncategorized")[:100]

    if normalized_name in category_cache:
        return category_cache[normalized_name]

    category = await get_category_by_name(db, normalized_name)

    if category is None:
        category = CategoryModel(name=normalized_name)
        add_category(db, category)
        await db.flush()

    category_cache[normalized_name] = category
    return category
