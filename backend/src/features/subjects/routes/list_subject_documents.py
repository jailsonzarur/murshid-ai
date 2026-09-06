from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import SubjectDocumentSchema
from src.features.subjects.services.subject_document_service import list_documents
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.get(
    "/{subject_id}/documents",
    operation_id="listSubjectDocuments",
    response_model=SuccessResponse[list[SubjectDocumentSchema]],
    responses={404: {"model": ErrorResponse}},
)
async def list_subject_documents_route(
    subject_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    documents = await list_documents(db, subject_id, current_user.id)
    return SuccessResponse(success=True, errors=None, data=documents)
