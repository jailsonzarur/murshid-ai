from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from pathlib import Path

from decouple import config
from openai import (
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)

from src.features.lectures.ai.audio_chunking import prepare_audio_for_whisper

logger = logging.getLogger(__name__)

TRANSCRIPTION_MODEL = str(config("TRANSCRIPTION_MODEL", default="whisper-1")).strip()
_MODEL = TRANSCRIPTION_MODEL
WHISPER_CONCURRENCY = 3

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


_OUTPUT_TOKEN_LIMIT = 2000


def _warn_if_truncated(transcription: object, filename: str) -> None:
    usage = getattr(transcription, "usage", None)
    output_tokens = getattr(usage, "output_tokens", None)
    if output_tokens is None:
        return
    if output_tokens >= _OUTPUT_TOKEN_LIMIT * 0.95:
        logger.warning(
            "transcription of %s used %d/%d output tokens; the text was likely truncated. "
            "Reduce CHUNK_TARGET_SECONDS.",
            filename,
            output_tokens,
            _OUTPUT_TOKEN_LIMIT,
        )


_PERMANENT_ERRORS = (AuthenticationError, PermissionDeniedError, BadRequestError)


def _error_code(exc: BaseException) -> str | None:
    code = getattr(exc, "code", None)
    if isinstance(code, str):
        return code

    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("code"), str):
            return error["code"]

    return None


def is_permanent_transcription_error(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        return _error_code(exc) == "insufficient_quota"
    return isinstance(exc, _PERMANENT_ERRORS)


async def transcribe_chunk_path(path: Path) -> str:
    audio_bytes = await asyncio.to_thread(path.read_bytes)
    return await transcribe_audio_chunk(audio_bytes, path.name)


async def transcribe_audio_chunk(audio_bytes: bytes, filename: str) -> str:
    client = _get_openai_client()
    try:
        transcription = await client.audio.transcriptions.create(
            model=_MODEL,
            file=(filename, audio_bytes),
            language="pt",
        )
        _warn_if_truncated(transcription, filename)
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


async def transcribe_audio_file(src_path: Path, duration_hint: float | None = None) -> str:
    sem = asyncio.Semaphore(WHISPER_CONCURRENCY)

    async def run(chunk_path: Path) -> str:
        async with sem:
            chunk_bytes = await asyncio.to_thread(chunk_path.read_bytes)
            return await transcribe_audio_chunk(chunk_bytes, chunk_path.name)

    with tempfile.TemporaryDirectory(prefix="whisper-chunk-") as tmp:
        chunks = await prepare_audio_for_whisper(src_path, Path(tmp), duration_hint)
        if len(chunks) == 1:
            return await run(chunks[0])

        transcripts = await asyncio.gather(*(run(chunk) for chunk in chunks))

    return " ".join(text.strip() for text in transcripts if text and text.strip())
