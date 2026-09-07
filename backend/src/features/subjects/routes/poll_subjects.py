from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import SubjectDetailSchema
from src.features.subjects.services.subject_service import list_subjects_by_ids
from src.shared.schemas.http import SuccessResponse

router = APIRouter()

MAX_IDS = 50


class PollSubjectsSchema(BaseModel):
    subject_ids: list[UUID] = Field(min_length=1, max_length=MAX_IDS)


@router.post(
    "/status",
    operation_id="pollSubjects",
    response_model=SuccessResponse[list[SubjectDetailSchema]],
)
async def poll_subjects_route(
    payload: PollSubjectsSchema,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subjects = await list_subjects_by_ids(db, current_user.id, payload.subject_ids)
    return SuccessResponse(success=True, errors=None, data=subjects)
