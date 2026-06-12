from __future__ import annotations

import json
import logging

from decouple import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = """
Você é um assistente educacional monitorando a transcrição ao vivo de uma aula.

Recebe um novo trecho transcrito e as listas atuais de tópicos e alertas já registrados.

Analise o trecho e determine:
1. Se um novo tópico principal foi iniciado ou um conceito significativamente novo foi introduzido.
   - Considere "novo" apenas se genuinamente diferente de todos os tópicos existentes.
   - Nomes de tópicos: máximo 5 palavras, em português.
2. Se há algo que o aluno deve prestar atenção especial (erro conceitual, conceito crítico, aviso importante).
   - Mensagens de alerta: máximo 100 caracteres, em português.

Retorne um JSON com exatamente esta estrutura:
{
  "topic": {"name": "nome do tópico", "is_new": true} ou null,
  "alert": {"message": "mensagem do alerta", "severity": "WARNING" ou "CRITICAL"} ou null
}

Retorne apenas o JSON, sem texto adicional.
""".strip()

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


async def extract_topic_and_alert(
    transcript: str,
    existing_topics: list[str],
    existing_alerts: list[str],
) -> dict:
    client = _get_openai_client()

    topics_text = "\n".join(f"- {t}" for t in existing_topics) if existing_topics else "Nenhum tópico ainda."
    alerts_text = "\n".join(f"- {a}" for a in existing_alerts) if existing_alerts else "Nenhum alerta ainda."

    user_message = (
        f"**Tópicos já registrados:**\n{topics_text}\n\n"
        f"**Alertas já registrados:**\n{alerts_text}\n\n"
        f"**Novo trecho transcrito:**\n{transcript}"
    )

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception:
        logger.exception("topic_alert_agent failed")
        return {}
