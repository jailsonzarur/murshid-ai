from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.categories.schemas.category_schemas import CategorySchema, CreateCategorySchema
from src.features.categories.services.category_service import create_category
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "",
    operation_id="createCategory",
    status_code=201,
    response_model=SuccessResponse[CategorySchema],
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def create_category_route(
    payload: CreateCategorySchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    category = await create_category(db, payload)
    return SuccessResponse(success=True, errors=None, data=category)
