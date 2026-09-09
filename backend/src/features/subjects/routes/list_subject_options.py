from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import SubjectOptionsResponse
from src.features.subjects.services.subject_service import list_paginated_subject_options
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.get(
    "/options",
    operation_id="listSubjectOptions",
    response_model=SuccessResponse[SubjectOptionsResponse],
)
async def list_subject_options_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Número da página")] = 1,
    search: Annotated[str | None, Query(description="Buscar por nome")] = None,
):
    data = await list_paginated_subject_options(db, current_user.id, page, search)
    return SuccessResponse(success=True, errors=None, data=data)
