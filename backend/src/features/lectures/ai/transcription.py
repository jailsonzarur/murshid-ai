from __future__ import annotations

from decouple import config
from openai import AsyncOpenAI

_MODEL = "gpt-4o-transcribe"

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


async def transcribe_audio_chunk(audio_bytes: bytes, filename: str) -> str:
    client = _get_openai_client()
    transcription = await client.audio.transcriptions.create(
        model=_MODEL,
        file=(filename, audio_bytes),
        language="pt",
    )
    return transcription.text
