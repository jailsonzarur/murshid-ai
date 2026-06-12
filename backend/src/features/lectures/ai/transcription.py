from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path

from decouple import config
from openai import AsyncOpenAI, BadRequestError

logger = logging.getLogger(__name__)

_MODEL = "whisper-1"

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


def _dump_failed_chunk(audio_bytes: bytes, filename: str) -> Path:
    suffix = os.path.splitext(filename)[1] or ".webm"
    dump_dir = Path(tempfile.gettempdir()) / "murshid-failed-chunks"
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_path = dump_dir / f"{uuid.uuid4().hex}{suffix}"
    dump_path.write_bytes(audio_bytes)
    return dump_path


async def transcribe_audio_chunk(audio_bytes: bytes, filename: str) -> str:
    client = _get_openai_client()
    try:
        transcription = await client.audio.transcriptions.create(
            model=_MODEL,
            file=(filename, audio_bytes),
            language="pt",
        )
        return transcription.text
    except BadRequestError:
        dump_path = _dump_failed_chunk(audio_bytes, filename)
        logger.exception(
            "OpenAI rejected audio chunk filename=%s size=%d dumped_to=%s",
            filename,
            len(audio_bytes),
            dump_path,
        )
        raise
