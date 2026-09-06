from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.subjects.schemas.subject_schemas import DeleteSubjectDocumentResponse
from src.features.subjects.services.subject_document_service import remove_document
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.delete(
    "/documents/{document_id}",
    operation_id="deleteSubjectDocument",
    response_model=SuccessResponse[DeleteSubjectDocumentResponse],
    responses={404: {"model": ErrorResponse}},
)
async def delete_subject_document_route(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await remove_document(db, document_id, current_user.id)
    return SuccessResponse(
        success=True,
        errors=None,
        data=DeleteSubjectDocumentResponse(
            document_id=document_id, message="Documento excluído com sucesso."
        ),
    )
