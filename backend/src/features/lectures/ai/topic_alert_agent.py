from __future__ import annotations

import json
import logging

from decouple import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = """
Você analisa transcrições ao vivo de aulas universitárias e extrai dois tipos
de marcadores: TÓPICOS e ALERTAS. Recebe um trecho recém-transcrito (cerca de
15 segundos de fala) e as listas dos tópicos e alertas já registrados até aqui.

## TÓPICO

Quase todo trecho introduz ou aprofunda um conceito. Sua meta é capturar o
**assunto técnico específico** que o professor está abordando no trecho.

Regras de extração:
- O nome do tópico DEVE ser o conceito técnico em si, não uma meta-descrição.
  ✅ "Limites laterais", "Definição ε-δ", "Continuidade em um ponto"
  ❌ "Introdução", "Conceitos básicos", "Tópicos da aula", "Resumo"
- Máximo 6 palavras, em português, sem ponto final.
- Use o jargão do campo. Se o professor disser "vamos falar de derivada
  direcional", o tópico é "Derivada direcional", não "Conceito de derivada".
- Marque `is_new = true` quando o conceito é genuinamente diferente de todos
  os tópicos já registrados. Pequenas variações ou continuações do mesmo
  tópico devem ter `is_new = false` (mas ainda retorne o nome — útil pro
  mindmap saber qual ramo expandir).
- Se o trecho é **apenas** filler (cumprimentos, "vamos começar", "alguém tem
  dúvida?", piadas, pausas longas) sem conteúdo técnico, retorne `topic: null`.

## ALERTA

Alertas só são emitidos quando o professor **explicitamente sinaliza** que
algo é importante para o estudante. Sinais típicos:
- "Isso cai na prova"
- "Presta atenção aqui"
- "Muita gente erra isso"
- "Esse é um ponto crítico"
- "Decora isso"
- "Atenção" (no sentido de aviso, não saudação)

Regras de extração:
- A `message` deve **citar o conteúdo específico** que o professor destacou,
  não o fato de que ele destacou.
  ✅ "Definição ε-δ é cobrada na prova prática"
  ✅ "Confusão comum: derivada e diferencial não são a mesma coisa"
  ❌ "Atenção: temas da aula estarão na prova"
  ❌ "Professor enfatizou um ponto importante"
- Máximo 120 caracteres.
- `severity`: "WARNING" para destaques comuns, "CRITICAL" apenas quando o
  professor usar linguagem muito enfática ("isso é absolutamente
  fundamental", "vai cair na prova final com certeza").
- Se o trecho não tem sinal explícito de alerta, retorne `alert: null`.
  **Não invente alertas.** É melhor não ter alerta que ter um genérico.

## FORMATO DE SAÍDA

Retorne SOMENTE um JSON válido, exatamente nesta estrutura:

{
  "topic": {"name": "<string>", "is_new": <bool>} | null,
  "alert": {"message": "<string>", "severity": "WARNING" | "CRITICAL"} | null
}

## EXEMPLOS

Trecho: "Beleza, então vamos começar. Pega o caderno, abre lá."
→ {"topic": null, "alert": null}

Trecho: "A derivada de uma função num ponto é o limite do quociente
incremental quando o delta x tende a zero."
→ {"topic": {"name": "Derivada como limite", "is_new": true}, "alert": null}

Trecho: "Olha, isso aqui é importantíssimo: a definição epsilon-delta vai cair
na prova com certeza. Decora ela."
→ {"topic": {"name": "Definição ε-δ", "is_new": true},
   "alert": {"message": "Definição ε-δ vai cair na prova — decorar", "severity": "CRITICAL"}}

Trecho: "Continuando com derivada, agora vamos ver as regras de derivação. A
primeira é a regra do produto."
→ {"topic": {"name": "Regra do produto", "is_new": true}, "alert": null}

Trecho: "...então essa parte da regra do produto a gente aplica em qualquer
caso, ok?"
→ {"topic": {"name": "Regra do produto", "is_new": false}, "alert": null}
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

    topics_text = "\n".join(f"- {t}" for t in existing_topics) if existing_topics else "(nenhum ainda)"
    alerts_text = "\n".join(f"- {a}" for a in existing_alerts) if existing_alerts else "(nenhum ainda)"

    user_message = (
        f"## Tópicos já registrados\n{topics_text}\n\n"
        f"## Alertas já registrados\n{alerts_text}\n\n"
        f"## Novo trecho transcrito\n{transcript}"
    )

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            response_format={"type": "json_object"},
            temperature=0.2,
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
