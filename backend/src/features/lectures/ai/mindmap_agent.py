from __future__ import annotations

import json
import logging

from decouple import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_LIVE_MODEL = "gpt-4o-mini"
_FINAL_MODEL = "gpt-4o"

_LIVE_SYSTEM_PROMPT = """
Você é um assistente educacional que mantém um mapa mental ao vivo de uma aula.

Recebe:
- O trecho mais recente transcrito
- A lista atualizada de tópicos detectados (em ordem de aparição)
- A lista de alertas registrados
- O mapa mental atual em formato Markmap (null se for o primeiro segmento)

Atualize o mapa mental para refletir o estado atual da aula.

Regras:
- Use # para o título da aula
- Use ## para tópicos principais
- Use ### para subtópicos quando naturalmente derivados do conteúdo transcrito
- Se houver alertas, adicione uma seção ## ⚠️ Alertas ao final com cada alerta como item de lista
- Retorne APENAS o markdown atualizado, sem explicações adicionais
- Mantenha o mapa conciso e hierárquico
""".strip()

_FINAL_SYSTEM_PROMPT = """
Você é um assistente educacional que gera materiais de estudo a partir de transcrições de aulas.

Recebe a transcrição completa de uma aula, a lista de tópicos detectados e os alertas registrados.

Produza um JSON com dois campos:
1. "summary": resumo em prosa da aula, organizado por tópicos, em português (máximo 500 palavras)
2. "mindmap_markdown": mapa mental hierárquico final em formato Markmap com:
   - # para o título
   - ## para tópicos principais
   - ### para subtópicos e conceitos-chave derivados da transcrição
   - Se houver alertas, seção ## ⚠️ Alertas ao final

Retorne apenas o JSON.
""".strip()

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


async def update_mindmap(
    transcript: str,
    topics: list[str],
    alerts: list[dict],
    current_mindmap: str | None,
    lecture_title: str | None,
) -> str:
    client = _get_openai_client()

    topics_text = "\n".join(f"- {t}" for t in topics) if topics else "Nenhum tópico ainda."
    alerts_text = (
        "\n".join(f"- [{a.get('severity', 'WARNING')}] {a.get('message', '')}" for a in alerts)
        if alerts
        else "Nenhum alerta."
    )
    current_map_text = current_mindmap or "(mapa ainda não iniciado)"

    user_message = (
        f"**Título da aula:** {lecture_title or 'Aula sem título'}\n\n"
        f"**Tópicos detectados:**\n{topics_text}\n\n"
        f"**Alertas:**\n{alerts_text}\n\n"
        f"**Mapa mental atual:**\n{current_map_text}\n\n"
        f"**Novo trecho transcrito:**\n{transcript}"
    )

    try:
        response = await client.chat.completions.create(
            model=_LIVE_MODEL,
            messages=[
                {"role": "system", "content": _LIVE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        return (response.choices[0].message.content or current_mindmap or "").strip()
    except Exception:
        logger.exception("mindmap_agent (live) failed")
        return current_mindmap or ""


async def generate_final_mindmap_and_summary(
    full_transcript: str,
    topics: list[str],
    alerts: list[dict],
    lecture_title: str | None,
) -> dict:
    client = _get_openai_client()

    topics_text = "\n".join(f"- {t}" for t in topics) if topics else "Nenhum tópico registrado."
    alerts_text = (
        "\n".join(f"- [{a.get('severity', 'WARNING')}] {a.get('message', '')}" for a in alerts)
        if alerts
        else "Nenhum alerta."
    )

    user_message = (
        f"**Título da aula:** {lecture_title or 'Aula sem título'}\n\n"
        f"**Tópicos detectados:**\n{topics_text}\n\n"
        f"**Alertas:**\n{alerts_text}\n\n"
        f"**Transcrição completa:**\n{full_transcript}"
    )

    try:
        response = await client.chat.completions.create(
            model=_FINAL_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _FINAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        return {
            "summary": result.get("summary", ""),
            "mindmap_markdown": result.get("mindmap_markdown", ""),
        }
    except Exception:
        logger.exception("mindmap_agent (final) failed")
        return {"summary": "", "mindmap_markdown": ""}
