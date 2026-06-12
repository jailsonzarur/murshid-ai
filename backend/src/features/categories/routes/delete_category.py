from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.categories.schemas.category_schemas import DeleteCategoryResponse
from src.features.categories.services.category_service import remove_category
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.delete(
    "/{category_id}",
    operation_id="deleteCategory",
    response_model=SuccessResponse[DeleteCategoryResponse],
    responses={404: {"model": ErrorResponse}},
)
async def delete_category_route(
    category_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await remove_category(db, category_id)
    return SuccessResponse(
        success=True,
        errors=None,
        data=DeleteCategoryResponse(category_id=category_id, message="Matéria excluída com sucesso."),
    )
