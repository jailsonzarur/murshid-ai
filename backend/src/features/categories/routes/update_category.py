from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.categories.schemas.category_schemas import CategorySchema, UpdateCategorySchema
from src.features.categories.services.category_service import update_category
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.patch(
    "/{category_id}",
    operation_id="updateCategory",
    response_model=SuccessResponse[CategorySchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_category_route(
    category_id: UUID,
    payload: UpdateCategorySchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    category = await update_category(db, category_id=category_id, payload=payload)
    return SuccessResponse(success=True, errors=None, data=category)
