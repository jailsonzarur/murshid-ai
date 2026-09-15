from __future__ import annotations

import logging
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

_client: OpenAI | None = None


@dataclass(frozen=True)
class Excerpt:
    document: str
    heading_path: str
    page: int | None
    text: str


@dataclass(frozen=True)
class TopicContext:
    title: str
    summary_section: str
    excerpts: list[Excerpt]


_SYSTEM_PROMPT = """Você escreve o **resumo guiado** de uma aula: a explicação do conteúdo
ensinado, ancorada na bibliografia da matéria.

Você recebe a transcrição da aula, os tópicos extraídos do resumo, e trechos da bibliografia
recuperados para cada tópico, cada um com o livro, o caminho da seção e a página.

## Regra principal

**Não invente nada.** Tudo o que você escrever tem que vir de uma destas duas fontes:

1. a transcrição da aula — o que a professora efetivamente disse
2. os trechos da bibliografia — a fonte da verdade sobre o conteúdo

Você não tem permissão para completar com conhecimento próprio, nem para "melhorar" a
explicação com informação que não está em nenhuma das duas. Se algo ficou incompleto na
aula e a bibliografia não cobre, diga isso em vez de preencher a lacuna.

Não invente número de página, nome de capítulo, nome de autor nem dado numérico. Use
apenas os metadados exatamente como vieram nos trechos.

## Como escrever

Uma seção em markdown por tópico, na ordem recebida, com `##` e o título do tópico.

Siga o que foi dado em aula: o recorte, a ordem e a ênfase são os da professora. A
bibliografia serve para embasar, precisar e completar o que foi dito — não para substituir
a aula por um capítulo de livro.

O resultado deve ser mais detalhado que um resumo comum. É material de estudo.

## Como citar

Cite no meio do texto, em prosa, mencionando livro, seção e página:

> A parede das Gram-positivas é espessa e rica em peptidoglicano, o que explica a retenção
> do cristal violeta na coloração de Gram (Murray, *Estrutura da Parede Celular*, p. 287).

Cite sempre que uma afirmação vier da bibliografia. Não use notas de rodapé, colchetes
numerados nem lista de referências no fim.

## Aula e bibliografia

Deixe claro o que é da aula e o que é do livro: "a professora apresentou", "em aula foi
dito", contra "a bibliografia descreve", "o livro define".

Quando divergirem, abra um bloco:

> **Divergência encontrada.** Em aula, [o que foi dito]. A bibliografia registra [o que o
> livro diz] (livro, seção, p. N).

Apresente os dois lados e pare. Não declare quem está certo e não corrija a professora —
pode ser recorte didático, edição diferente ou trecho recuperado fora de contexto.

## Tópico sem bibliografia

Quando um tópico vier sem trechos, explique-o **apenas** com o que foi dito em aula e abra
a seção com:

> *Este tópico não tem respaldo na bibliografia anexada à matéria.*

Não force ligação com trecho de outro tópico e não complete com conhecimento próprio.

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

    return response.choices[0].message.content or ""


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
                f"**{excerpt.document} — {excerpt.heading_path}{page}**\n{excerpt.text.strip()}"
            )

    return "\n\n".join(blocks)


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
