from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import cast

from decouple import config
from openai import OpenAI
from openai.types.shared.reasoning_effort import ReasoningEffort

logger = logging.getLogger(__name__)

_MODEL = str(config("GUIDED_SUMMARY_MODEL", default="gpt-5.6-luna")).strip()
_REASONING: ReasoningEffort = cast(
    ReasoningEffort, str(config("GUIDED_SUMMARY_REASONING", default="xhigh")).strip()
)

CITATION = re.compile(r"\[\[(\d+)\]\]")

_client: OpenAI | None = None


@dataclass(frozen=True)
class Excerpt:
    number: int
    document: str
    heading_path: str
    page: int | None
    text: str


@dataclass(frozen=True)
class TopicContext:
    title: str
    summary_section: str
    excerpts: list[Excerpt]


_SYSTEM_PROMPT = """Você escreve o **resumo guiado** de uma aula: uma explicação do conteúdo
ancorada na bibliografia da matéria.

Você recebe a transcrição da aula, os tópicos extraídos do resumo, e trechos numerados da
bibliografia recuperados para cada tópico.

## Como escrever

Uma seção em markdown por tópico, na ordem recebida, com `##` e o título do tópico.

Explique o conteúdo com profundidade, usando a transcrição para saber o que foi de fato
dito em aula e os trechos para embasar. O resultado deve ser mais detalhado que um resumo
comum — é material de estudo, não índice.

## Citações

Ao afirmar algo que vem de um trecho, cite com o número dele entre colchetes duplos, assim:
`[[3]]`. Use apenas números que existem no contexto daquele tópico. Nunca invente um número
e nunca cite um trecho que não sustente a afirmação.

## Aula e bibliografia

Deixe sempre claro o que é da aula e o que é do livro. Use formulações como "a professora
apresentou", "em aula foi dito", contra "a bibliografia descreve", "o livro define".

Quando a aula e a bibliografia **divergirem**, abra um bloco:

> **Divergência encontrada.** Em aula, [o que foi dito]. A bibliografia registra [o que o
> livro diz] [[n]].

Apresente os dois lados e pare aí. Não declare quem está certo, não corrija a professora e
não trate a divergência como erro — pode ser recorte didático, edição diferente ou trecho
recuperado fora de contexto.

## Tópico sem bibliografia

Quando um tópico vier sem trechos, explique-o a partir da aula e abra a seção com:

> *Este tópico não tem respaldo na bibliografia anexada à matéria.*

Não force ligação com trecho de outro tópico.

Responda apenas com o markdown do resumo guiado, sem preâmbulo."""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _client


def build_guided_summary(
    transcript: str, topics: list[TopicContext], lecture_title: str | None, subject_name: str | None
) -> str:
    if not topics:
        return ""

    header = " — ".join(part for part in (subject_name, lecture_title) if part)
    user_message = "\n\n".join(
        part
        for part in (
            f"# {header}" if header else "",
            f"## Transcrição da aula\n\n{transcript.strip()}",
            _render_topics(topics),
        )
        if part
    )

    try:
        response = _get_client().chat.completions.create(
            model=_MODEL,
            reasoning_effort=_REASONING,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception:
        logger.exception("guided_summary_agent request failed")
        return ""

    _log_usage(response)

    content = response.choices[0].message.content or ""
    return drop_unknown_citations(content, _known_numbers(topics))


def _render_topics(topics: list[TopicContext]) -> str:
    blocks: list[str] = ["## Tópicos e trechos da bibliografia"]

    for topic in topics:
        blocks.append(f"\n### {topic.title}\n\n{topic.summary_section.strip()}")
        if not topic.excerpts:
            blocks.append("_Nenhum trecho da bibliografia foi recuperado para este tópico._")
            continue
        for excerpt in topic.excerpts:
            page = f", p. {excerpt.page}" if excerpt.page else ""
            blocks.append(
                f"[{excerpt.number}] {excerpt.document} — {excerpt.heading_path}{page}\n"
                f"{excerpt.text.strip()}"
            )

    return "\n\n".join(blocks)


def _known_numbers(topics: list[TopicContext]) -> set[int]:
    return {excerpt.number for topic in topics for excerpt in topic.excerpts}


def drop_unknown_citations(markdown: str, known: set[int]) -> str:
    """O modelo cita números que não existem. Deixar passar quebraria o badge no
    frontend, que não teria trecho para abrir."""
    removed: list[str] = []

    def replace(match: re.Match[str]) -> str:
        if int(match.group(1)) in known:
            return match.group(0)
        removed.append(match.group(1))
        return ""

    cleaned = CITATION.sub(replace, markdown)
    if removed:
        logger.warning("guided_summary: descartadas citações inexistentes %s", sorted(set(removed)))
    return cleaned


def _log_usage(response: object) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    details = getattr(usage, "completion_tokens_details", None)
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    logger.info(
        "guided_summary usage model=%s reasoning=%s in=%s out=%s reasoning_tokens=%s cached=%s",
        _MODEL,
        _REASONING,
        getattr(usage, "prompt_tokens", "?"),
        getattr(usage, "completion_tokens", "?"),
        getattr(details, "reasoning_tokens", "?") if details else "?",
        getattr(prompt_details, "cached_tokens", "?") if prompt_details else "?",
    )
