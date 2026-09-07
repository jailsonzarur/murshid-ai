from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import PaginatedSubjectsSchema
from src.features.subjects.services.subject_service import (
    DEFAULT_ITEMS_PER_PAGE,
    list_all_subjects,
)
from src.shared.schemas.http import SuccessResponse

router = APIRouter()

MAX_ITEMS_PER_PAGE = 100


@router.get(
    "",
    operation_id="listSubjects",
    response_model=SuccessResponse[PaginatedSubjectsSchema],
)
async def list_subjects_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Número da página")] = 1,
    items_per_page: Annotated[
        int, Query(ge=1, le=MAX_ITEMS_PER_PAGE, description="Itens por página")
    ] = DEFAULT_ITEMS_PER_PAGE,
):
    data = await list_all_subjects(db, current_user.id, page=page, items_per_page=items_per_page)
    return SuccessResponse(success=True, errors=None, data=data)
