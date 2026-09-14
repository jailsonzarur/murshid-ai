from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import GuidedCitationSchema
from src.features.lectures.services.lecture_service import list_guided_citations
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/{lecture_id}/guided-citations",
    operation_id="listLectureGuidedCitations",
    response_model=SuccessResponse[list[GuidedCitationSchema]],
    responses={404: {"model": ErrorResponse}},
)
async def list_guided_citations_route(
    lecture_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    citations = await list_guided_citations(db, lecture_id, current_user.id)
    return SuccessResponse(success=True, errors=None, data=citations)
