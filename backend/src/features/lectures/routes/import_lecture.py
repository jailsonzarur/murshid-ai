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
MAX_TOTAL_BYTES = 400 * 1024 * 1024  # teto agregado por aula
ALLOWED_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "video/mp4",
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


def _as_mb(value: int) -> int:
    return value // (1024 * 1024)


def _parse_durations(durations: str, file_count: int) -> list:
    try:
        parsed = json.loads(durations)
    except json.JSONDecodeError:
        raise _validation_error("Campo `durations` precisa ser um JSON válido (array de números).")

    if not isinstance(parsed, list) or len(parsed) != file_count:
        raise _validation_error(
            "Forneça uma duração (em segundos) para cada arquivo, na mesma ordem.",
        )

    return parsed


def _validate_uploads(files: list[UploadFile], parsed_durations: list) -> list[float]:
    validated: list[float] = []
    total_bytes = 0

    for index, upload in enumerate(files):
        label = upload.filename or index + 1

        size = upload.size
        if size is None:
            raise _validation_error(f"Não foi possível determinar o tamanho do arquivo {label}.")
        if size == 0:
            raise _validation_error(f"Arquivo {label} está vazio.")
        if size > MAX_FILE_BYTES:
            raise _validation_error(f"Arquivo {label} excede o limite de {_as_mb(MAX_FILE_BYTES)} MB.")

        total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            raise _validation_error(
                f"Os arquivos somam mais de {_as_mb(MAX_TOTAL_BYTES)} MB. Envie menos arquivos por aula.",
            )

        mime = (upload.content_type or "").lower()
        if mime and mime not in ALLOWED_MIME_TYPES:
            raise _validation_error(
                f"Formato não suportado: {mime}. Aceitos: mp3, mp4, m4a, wav, webm, ogg, opus.",
            )

        try:
            duration = float(parsed_durations[index])
        except (TypeError, ValueError):
            raise _validation_error(f"Duração inválida para o arquivo {index + 1}.")
        if duration <= 0:
            raise _validation_error(f"Duração inválida para o arquivo {index + 1}.")

        validated.append(duration)

    return validated


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
    subject_id: Annotated[UUID | None, Form()] = None,
):
    if not files:
        raise _validation_error("Envie pelo menos um arquivo de áudio.")
    if len(files) > MAX_FILES:
        raise _validation_error(f"Máximo de {MAX_FILES} arquivos por aula.")

    parsed_durations = _parse_durations(durations, len(files))
    validated_durations = _validate_uploads(files, parsed_durations)

    audio_items: list[ImportAudioItem] = []
    for index, upload in enumerate(files):
        audio_items.append(
            ImportAudioItem(
                filename=upload.filename or f"audio_{index + 1}",
                stream=upload.file,
                size=upload.size or 0,
                content_type=upload.content_type,
                duration=validated_durations[index],
            )
        )

    lecture = await start_import_lecture(
        db,
        user_id=current_user.id,
        title=title.strip() if title else None,
        subject_id=subject_id,
        audio_items=audio_items,
    )
    return SuccessResponse(success=True, errors=None, data=lecture)
