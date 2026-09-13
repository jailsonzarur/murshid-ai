from __future__ import annotations

import logging

from decouple import config
from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL = str(config("EMBEDDING_MODEL", default="text-embedding-3-small")).strip()
BATCH_SIZE = int(str(config("EMBEDDING_BATCH_SIZE", default="100")).strip())

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = _get_client()
    vectors: list[list[float]] = []
    total_tokens = 0

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        response = client.embeddings.create(model=MODEL, input=batch)
        vectors.extend(item.embedding for item in response.data)
        total_tokens += response.usage.total_tokens

    logger.info(
        "embedding usage model=%s texts=%d tokens=%d", MODEL, len(texts), total_tokens
    )
    return vectors
