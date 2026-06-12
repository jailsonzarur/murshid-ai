from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.categories.schemas.category_schemas import CategorySchema
from src.features.categories.services.category_service import list_all_categories
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.get(
    "",
    operation_id="listCategories",
    response_model=SuccessResponse[list[CategorySchema]],
)
async def list_categories_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    categories = await list_all_categories(db)
    return SuccessResponse(success=True, errors=None, data=categories)
