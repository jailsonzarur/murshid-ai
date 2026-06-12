from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import ProcessSegmentResponseSchema
from src.features.lectures.services.lecture_service import process_segment
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()


@router.post(
    "/{lecture_id}/segments",
    operation_id="processLectureSegment",
    status_code=201,
    response_model=SuccessResponse[ProcessSegmentResponseSchema],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def process_segment_route(
    lecture_id: UUID,
    audio: Annotated[UploadFile, File()],
    sequence: Annotated[int, Form()],
    duration: Annotated[float, Form()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    audio_bytes = await audio.read()
    filename = audio.filename or f"segment_{sequence}.webm"
    segment = await process_segment(
        db,
        lecture_id=lecture_id,
        user_id=current_user.id,
        audio_bytes=audio_bytes,
        filename=filename,
        sequence=sequence,
        duration=duration,
    )
    return SuccessResponse(success=True, errors=None, data=segment)
