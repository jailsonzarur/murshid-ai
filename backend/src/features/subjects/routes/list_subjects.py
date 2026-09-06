from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import SubjectSchema
from src.features.subjects.services.subject_service import list_all_subjects
from src.shared.schemas.http import SuccessResponse

router = APIRouter()


@router.get(
    "",
    operation_id="listSubjects",
    response_model=SuccessResponse[list[SubjectSchema]],
)
async def list_subjects_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subjects = await list_all_subjects(db, current_user.id)
    return SuccessResponse(success=True, errors=None, data=subjects)
