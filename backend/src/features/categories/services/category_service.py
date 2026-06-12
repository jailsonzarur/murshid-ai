from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.categories.models import CategoryModel
from src.features.categories.repository import (
    add_category,
    delete_category,
    get_category_by_id,
    get_category_by_name,
    list_categories,
)
from src.features.categories.schemas.category_schemas import (
    CategorySchema,
    CreateCategorySchema,
    UpdateCategorySchema,
)


def _normalize_name(raw: str) -> str:
    return " ".join(raw.strip().split())[:100]


async def get_or_create_category(
    db: AsyncSession,
    category_cache: dict[str, CategoryModel],
    category_name: str,
) -> CategoryModel:
    normalized_name = _normalize_name(category_name) or "Uncategorized"

    if normalized_name in category_cache:
        return category_cache[normalized_name]

    category = await get_category_by_name(db, normalized_name)

    if category is None:
        category = CategoryModel(name=normalized_name)
        add_category(db, category)
        await db.flush()

    category_cache[normalized_name] = category
    return category


async def list_all_categories(db: AsyncSession) -> list[CategorySchema]:
    categories = await list_categories(db)
    return [CategorySchema.model_validate(c) for c in categories]


async def create_category(db: AsyncSession, payload: CreateCategorySchema) -> CategorySchema:
    normalized = _normalize_name(payload.name)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Nome inválido."], "data": None},
        )

    existing = await get_category_by_name(db, normalized)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "errors": ["Já existe uma matéria com esse nome."], "data": None},
        )

    category = CategoryModel(name=normalized)
    add_category(db, category)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "errors": ["Já existe uma matéria com esse nome."], "data": None},
        )
    await db.refresh(category)
    return CategorySchema.model_validate(category)


async def update_category(
    db: AsyncSession,
    *,
    category_id: UUID,
    payload: UpdateCategorySchema,
) -> CategorySchema:
    category = await get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Matéria não encontrada."], "data": None},
        )

    normalized = _normalize_name(payload.name)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Nome inválido."], "data": None},
        )

    if normalized != category.name:
        conflicting = await get_category_by_name(db, normalized)
        if conflicting is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"success": False, "errors": ["Já existe uma matéria com esse nome."], "data": None},
            )

    category.name = normalized
    await db.commit()
    await db.refresh(category)
    return CategorySchema.model_validate(category)


async def remove_category(db: AsyncSession, category_id: UUID) -> None:
    category = await get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Matéria não encontrada."], "data": None},
        )
    await delete_category(db, category)
    await db.commit()
