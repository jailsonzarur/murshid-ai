from __future__ import annotations

import json
import logging
from typing import TypedDict, cast

from decouple import config
from openai import OpenAI
from openai.types.shared.reasoning_effort import ReasoningEffort

logger = logging.getLogger(__name__)

_MODEL = str(config("GUIDED_TOPICS_MODEL", default="gpt-5.6-luna")).strip()
_REASONING: ReasoningEffort = cast(
    ReasoningEffort, str(config("GUIDED_TOPICS_REASONING", default="medium")).strip()
)

_client: OpenAI | None = None


class GuidedTopic(TypedDict):
    title: str
    query: str
    anchor: str


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "query": {"type": "string"},
                    "anchor": {"type": "string"},
                },
                "required": ["title", "query", "anchor"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["topics"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = """Você recebe o resumo de uma aula e a transcrição dela.

Para cada seção do resumo, devolva um tópico com três campos:

- **title**: o título da seção, como está no resumo.
- **query**: o texto da seção, praticamente na íntegra. Esse texto será usado para buscar
  trechos parecidos na bibliografia da matéria por similaridade semântica, então ele deve
  ser prosa corrente com a mesma terminologia da seção. Não resuma, não transforme em
  palavras-chave e não escreva uma pergunta.
- **anchor**: uma frase curta copiada **literalmente** da transcrição, do ponto em que
  aquele assunto começa a ser tratado. Copie exatamente como está, mesmo com erros de
  transcrição. Se não encontrar, devolva string vazia.

Uma seção do resumo equivale a um tópico. Não invente tópicos que não estejam no resumo e
não junte duas seções num tópico só."""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _client


def extract_topics(summary: str, transcript: str) -> list[GuidedTopic]:
    if not summary.strip():
        return []

    user_message = (
        f"## Resumo da aula\n\n{summary.strip()}\n\n"
        f"## Transcrição da aula\n\n{transcript.strip()}"
    )

    try:
        response = _get_client().chat.completions.create(
            model=_MODEL,
            reasoning_effort=_REASONING,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "guided_topics",
                    "strict": True,
                    "schema": _RESPONSE_SCHEMA,
                },
            },
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception:
        logger.exception("guided_topics_agent request failed")
        return []

    _log_usage(response)

    content = response.choices[0].message.content
    if not content:
        logger.warning("guided_topics_agent returned empty content")
        return []

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.exception("guided_topics_agent returned invalid JSON")
        return []

    return [topic for topic in parsed.get("topics", []) if topic.get("query", "").strip()]


def _log_usage(response: object) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    details = getattr(usage, "completion_tokens_details", None)
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    logger.info(
        "guided_topics usage model=%s reasoning=%s in=%s out=%s reasoning_tokens=%s cached=%s",
        _MODEL,
        _REASONING,
        getattr(usage, "prompt_tokens", "?"),
        getattr(usage, "completion_tokens", "?"),
        getattr(details, "reasoning_tokens", "?") if details else "?",
        getattr(prompt_details, "cached_tokens", "?") if prompt_details else "?",
    )
