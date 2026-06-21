from __future__ import annotations

import logging

from decouple import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = """
Você é um observador discreto de uma aula universitária. Você recebe os
últimos trechos transcritos da aula (com ênfase no MAIS RECENTE) e produz
UMA frase curta e descritiva do que está acontecendo agora na aula.

Essa frase é exibida ao vivo pro estudante como um "ticker" — um sinal
mínimo de que a transcrição está rolando e do que o professor está abordando
naquele momento.

## Regras

- **Uma frase só.** Entre 12 e 30 palavras.
- **Português, prosa direta.** Sem markdown, sem emojis, sem aspas.
- **Descreva o que o professor está fazendo/explicando**, não o que o aluno
  deveria fazer. Exemplos bons:
  - "Professor introduzindo o conceito de derivadas parciais com exemplo gráfico."
  - "Demonstração da regra do produto sendo construída no quadro."
  - "Discussão sobre limites laterais e a notação x → a+."
- **Foque no trecho mais recente** — os anteriores são só contexto.
- Se o trecho mais recente for **filler** (cumprimentos, pausas, perguntas
  sem conteúdo técnico, "alguém tem dúvida?"), descreva isso de forma neutra:
  - "Pausa para perguntas dos alunos."
  - "Início da aula sendo organizado."
- **Não invente conteúdo** que não esteja na transcrição. Se o trecho está
  vago ou ruidoso, descreva neutramente: "Continuação da explicação anterior."

Retorne APENAS a frase, sem qualquer prefixo ou explicação adicional.
""".strip()

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


async def generate_live_insight(recent_transcripts: list[str]) -> str | None:
    """Gera uma frase descritiva do trecho mais recente da aula.

    `recent_transcripts` deve estar ordenado do mais antigo pro mais recente.
    O último é o foco principal; os anteriores são contexto.

    Retorna None em caso de falha — o frontend mantém o insight anterior.
    """
    if not recent_transcripts:
        return None

    client = _get_openai_client()

    parts = []
    for index, transcript in enumerate(recent_transcripts):
        label = "MAIS RECENTE" if index == len(recent_transcripts) - 1 else f"trecho anterior #{index + 1}"
        parts.append(f"[{label}]\n{transcript.strip()}")
    user_message = "\n\n".join(parts)

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            return None
        return content.strip()
    except Exception:
        logger.exception("live_insight_agent failed")
        return None
