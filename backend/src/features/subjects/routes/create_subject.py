from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import SubjectDetailSchema
from src.features.subjects.services.subject_document_service import validate_documents
from src.features.subjects.services.subject_service import create_subject
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "",
    operation_id="createSubject",
    status_code=201,
    response_model=SuccessResponse[SubjectDetailSchema],
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def create_subject_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    documents: Annotated[list[UploadFile] | None, File()] = None,
):
    resolved_documents = [document for document in (documents or []) if document.filename]
    validate_documents(resolved_documents)

    subject = await create_subject(
        db,
        current_user.id,
        name=name,
        documents=resolved_documents,
    )
    return SuccessResponse(success=True, errors=None, data=subject)
