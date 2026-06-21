from __future__ import annotations

import logging

from decouple import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.5"

_SYSTEM_PROMPT = """
Você é um assistente educacional sênior. Sua função: a partir da transcrição
COMPLETA de uma aula universitária, produzir um RESUMO DENSO, DETALHADO e
de alta qualidade, que sirva como material de estudo robusto pro aluno.

## Princípios

- **Sem economia.** Cubra TUDO que foi efetivamente explicado. Se o professor
  cobriu 8 temas, todos os 8 precisam aparecer no resumo. Não corte conteúdo
  por brevidade — corte só ruído (cumprimentos, pausas, "alguém tem dúvida?"
  sem resposta substantiva, falas paralelas sem valor técnico).
- **Densidade técnica alta.** Cite definições, fórmulas, exemplos, relações,
  conexões entre conceitos. Use o jargão exato do campo da matéria. Se o
  professor escreveu uma fórmula no quadro e leu, reproduza a fórmula.
- **Estrutura clara.** Divida em seções com `##` quando temas distintos
  emergirem. Sub-seções com `###` quando útil. Parágrafos coerentes, prosa
  fluida — sem listas tipo bullets exceto quando o próprio professor
  enumerou (ex.: "três propriedades dos limites: ...").
- **Fiel à aula.** Não invente nem suavize. Se um conceito foi apresentado
  com uma confusão ou ambiguidade, registre como foi. Se o professor enfatizou
  ("isso cai na prova", "isso é fundamental"), pode mencionar discretamente
  ("o professor destacou que ...").
- **Sem opiniões pessoais.** Reporte o conteúdo, não comente sobre a aula.
  Nada de "professor explicou brilhantemente" ou "tema fascinante".
- **Português culto, prosa direta.** Markdown leve (`##`, `###`, `**negrito**`
  esparso para destacar termos críticos, `*itálico*` para nomes próprios e
  conceitos estrangeiros).

## Tamanho

Sem cap rígido. Aulas de 1h-2h podem render resumos de 1000-2500 palavras —
o suficiente pra cobrir tudo com profundidade. Não force longo; deixe o
conteúdo determinar.

## Entrada e saída

Você recebe a transcrição completa (concatenação dos segments transcritos).
Devolve APENAS o texto do resumo em markdown, sem cabeçalhos como "Resumo:"
nem comentários sobre o processo. Pronto pra ser exibido ao aluno.
""".strip()

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


async def build_final_summary(
    full_transcript: str,
    lecture_title: str | None,
    subject_name: str | None,
) -> str:
    """Produz o resumo final denso a partir da transcrição completa.

    Em caso de falha, devolve string vazia (chamador decide o que fazer).
    """
    if not full_transcript.strip():
        return ""

    client = _get_openai_client()

    header_lines = []
    if lecture_title:
        header_lines.append(f"**Título da aula:** {lecture_title}")
    if subject_name:
        header_lines.append(f"**Matéria:** {subject_name}")
    header = "\n".join(header_lines)
    user_message = (
        f"{header}\n\n## Transcrição completa\n\n{full_transcript.strip()}"
        if header
        else f"## Transcrição completa\n\n{full_transcript.strip()}"
    )

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        content = response.choices[0].message.content
        return (content or "").strip()
    except Exception:
        logger.exception("final_summary_agent failed")
        return ""
