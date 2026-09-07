from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import SubjectOptionSchema
from src.features.subjects.services.subject_service import list_all_subject_options
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.get(
    "/options",
    operation_id="listSubjectOptions",
    response_model=SuccessResponse[list[SubjectOptionSchema]],
)
async def list_subject_options_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    options = await list_all_subject_options(db, current_user.id)
    return SuccessResponse(success=True, errors=None, data=options)
