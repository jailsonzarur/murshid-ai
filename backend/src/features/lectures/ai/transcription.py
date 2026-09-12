from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from pathlib import Path

from decouple import config
from openai import (
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from src.features.lectures.ai.audio_chunking import prepare_audio_for_whisper

logger = logging.getLogger(__name__)

TRANSCRIPTION_PROVIDER = str(config("TRANSCRIPTION_PROVIDER", default="openai")).strip().lower()
TRANSCRIPTION_MODEL = str(
    config(
        "TRANSCRIPTION_MODEL",
        default="@cf/openai/whisper-large-v3-turbo" if TRANSCRIPTION_PROVIDER == "cloudflare" else "whisper-1",
    )
).strip()
_MODEL = TRANSCRIPTION_MODEL
TRANSCRIPTION_LANGUAGE = str(config("TRANSCRIPTION_LANGUAGE", default="pt")).strip()
TRANSCRIPTION_CONDITION_ON_PREVIOUS: bool = str(
    config("TRANSCRIPTION_CONDITION_ON_PREVIOUS", default="false")
).strip().lower() in {"1", "true", "yes", "on"}
WHISPER_CONCURRENCY = 3

_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


def _cloudflare_transcribe(audio_bytes: bytes, filename: str) -> str:
    import base64

    import httpx

    account_id = str(config("CLOUDFLARE_ACCOUNT_ID"))
    token = str(config("CLOUDFLARE_API_TOKEN"))

    payload: dict[str, object] = {
        "audio": base64.b64encode(audio_bytes).decode("utf-8"),
        "language": TRANSCRIPTION_LANGUAGE,
        "task": "transcribe",
        "condition_on_previous_text": TRANSCRIPTION_CONDITION_ON_PREVIOUS,
    }

    response = httpx.post(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{_MODEL}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=httpx.Timeout(300.0),
    )
    response.raise_for_status()
    body = response.json()

    if not body.get("success", False):
        raise RuntimeError(f"cloudflare transcription failed: {body.get('errors')}")

    text = str(body["result"].get("text", ""))
    logger.info(
        "transcription usage provider=cloudflare model=%s file=%s bytes=%d chars=%d cond_prev=%s",
        _MODEL,
        filename,
        len(audio_bytes),
        len(text),
        TRANSCRIPTION_CONDITION_ON_PREVIOUS,
    )
    return text


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


def transcribe_chunk_path(path: Path) -> str:
    return transcribe_audio_chunk(path.read_bytes(), path.name)


def transcribe_audio_chunk(audio_bytes: bytes, filename: str) -> str:
    if TRANSCRIPTION_PROVIDER == "cloudflare":
        return _cloudflare_transcribe(audio_bytes, filename)

    client = _get_openai_client()
    try:
        transcription = client.audio.transcriptions.create(
            model=_MODEL,
            file=(filename, audio_bytes),
            language=TRANSCRIPTION_LANGUAGE,
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
            return await asyncio.to_thread(transcribe_chunk_path, chunk_path)

    with tempfile.TemporaryDirectory(prefix="whisper-chunk-") as tmp:
        chunks = await prepare_audio_for_whisper(src_path, Path(tmp), duration_hint)
        if len(chunks) == 1:
            return await run(chunks[0])

        transcripts = await asyncio.gather(*(run(chunk) for chunk in chunks))

    return " ".join(text.strip() for text in transcripts if text and text.strip())
