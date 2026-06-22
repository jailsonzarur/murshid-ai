from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.features.auth.utils import CurrentUser, get_current_user
from src.features.lectures.schemas.lecture_schemas import LectureSummarySchema
from src.features.lectures.services.lecture_service import ImportAudioItem, start_import_lecture
from src.shared.schemas.http import ErrorResponse, SuccessResponse

router = APIRouter()

MAX_FILES = 10
MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB — worker fatia em pedaços p/ Whisper
ALLOWED_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/opus",
}


def _validation_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"success": False, "errors": [message], "data": None},
    )


@router.post(
    "/import",
    operation_id="importLecture",
    status_code=201,
    response_model=SuccessResponse[LectureSummarySchema],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def import_lecture_route(
    files: Annotated[list[UploadFile], File()],
    durations: Annotated[str, Form()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    title: Annotated[str | None, Form()] = None,
    category_id: Annotated[UUID | None, Form()] = None,
):
    if not files:
        raise _validation_error("Envie pelo menos um arquivo de áudio.")
    if len(files) > MAX_FILES:
        raise _validation_error(f"Máximo de {MAX_FILES} arquivos por aula.")

    try:
        parsed_durations = json.loads(durations)
    except json.JSONDecodeError:
        raise _validation_error("Campo `durations` precisa ser um JSON válido (array de números).")

    if not isinstance(parsed_durations, list) or len(parsed_durations) != len(files):
        raise _validation_error(
            "Forneça uma duração (em segundos) para cada arquivo, na mesma ordem.",
        )

    audio_items: list[ImportAudioItem] = []
    for index, upload in enumerate(files):
        content = await upload.read()
        if not content:
            raise _validation_error(f"Arquivo {upload.filename or index + 1} está vazio.")
        if len(content) > MAX_FILE_BYTES:
            raise _validation_error(
                f"Arquivo {upload.filename or index + 1} excede o limite de 200 MB.",
            )
        mime = (upload.content_type or "").lower()
        if mime and mime not in ALLOWED_MIME_TYPES:
            raise _validation_error(
                f"Formato não suportado: {mime}. Aceitos: mp3, m4a, wav, webm, ogg, opus.",
            )

        try:
            duration = float(parsed_durations[index])
        except (TypeError, ValueError):
            raise _validation_error(f"Duração inválida para o arquivo {index + 1}.")
        if duration <= 0:
            raise _validation_error(f"Duração inválida para o arquivo {index + 1}.")

        audio_items.append(
            ImportAudioItem(
                filename=upload.filename or f"audio_{index + 1}",
                content=content,
                content_type=upload.content_type,
                duration=duration,
            )
        )

    lecture = await start_import_lecture(
        db,
        user_id=current_user.id,
        title=title.strip() if title else None,
        category_id=category_id,
        audio_items=audio_items,
    )
    return SuccessResponse(success=True, errors=None, data=lecture)
