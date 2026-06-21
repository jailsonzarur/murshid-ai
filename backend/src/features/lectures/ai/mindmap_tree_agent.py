from __future__ import annotations

import json
import logging
from typing import TypedDict

from decouple import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.5"


class MindmapNode(TypedDict):
    id: str
    parent_id: str | None
    label: str
    summary: str


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "description": (
                "Árvore COMPLETA do mapa mental da aula. Estrutura plana com "
                "parent_id apontando para outro id da lista, ou null para nós "
                "raiz. Inclua todos os conceitos cobertos, com hierarquia rica."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": (
                            "ID único curto (ex.: 'n1', 'n2', 'n3', ...). "
                            "Numere sequencialmente do n1 em diante."
                        ),
                    },
                    "parent_id": {
                        "type": ["string", "null"],
                        "description": (
                            "ID do nó pai. null para nós raiz. Deve "
                            "referenciar um ID presente neste mesmo array."
                        ),
                    },
                    "label": {
                        "type": "string",
                        "description": (
                            "Nome do conceito em português, usando jargão "
                            "técnico do campo. Máximo 6 palavras. Exemplos: "
                            "'Definição ε-δ', 'Regra do produto', "
                            "'Continuidade em um ponto'. NÃO use rótulos "
                            "genéricos como 'Introdução' ou 'Conceitos básicos'."
                        ),
                    },
                    "summary": {
                        "type": "string",
                        "description": (
                            "Descrição substantiva do conceito (2 a 4 frases). "
                            "Cite definições, fórmulas e relações conforme "
                            "apareceram na aula. Use jargão técnico fiel ao "
                            "professor. Vá direto ao conteúdo — sem 'o "
                            "professor explicou que...'."
                        ),
                    },
                },
                "required": ["id", "parent_id", "label", "summary"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["nodes"],
    "additionalProperties": False,
}


_SYSTEM_PROMPT = """
Você é um cartógrafo de conhecimento. A partir da transcrição COMPLETA de uma
aula universitária, você constrói um MAPA MENTAL hierárquico com todos os
conceitos cobertos, organizados em árvore.

## Princípios

- **Hierarquia profunda e bem estruturada.** Identifique os 2-5 grandes temas
  da aula (nós raiz, `parent_id=null`) e, sob cada um, organize subtemas e
  conceitos específicos com vários níveis quando o conteúdo justificar.
  Aulas técnicas tipicamente rendem árvores de 3-4 níveis de profundidade.
- **Granularidade rica.** Cada conceito tecnicamente distinto vira um nó
  próprio. NÃO empilhe vários sub-conceitos numa única `summary` longa —
  prefira sub-nós. Uma aula de 1h normalmente rende **30-70 nós**; uma de 2h
  pode chegar a 100+. Não force quantidade, mas também não economize.
- **Labels precisos.** O nome do conceito em si, máximo 6 palavras, jargão
  técnico. ✅ "Derivada parcial", "Definição ε-δ", "Regra do produto",
  "Teorema do confronto". ❌ "Introdução", "Conceitos básicos", "Tópicos
  importantes".
- **Summaries substantivas.** Cada nó tem uma summary de 2-4 frases que
  capturam o que foi efetivamente dito sobre o conceito: definição, fórmula
  (se houver), exemplo, ou relação com outros conceitos. Se o professor
  destacou ("isso cai na prova", "muita gente erra"), pode aparecer
  discretamente na summary.
- **Hierarquia semântica, não temporal.** A ordem em que o professor explicou
  não dita a hierarquia. Se ele falou de RAG, MCP e Tools antes de mencionar
  que são "ferramentas de agentes de IA", o nó "Agentes de IA" é o pai e os
  três viram filhos dele — mesmo que tenham sido mencionados antes na aula.
- **IDs sequenciais.** Use IDs curtos: n1, n2, n3, ... Cada ID deve ser único.
  Cada `parent_id` (não null) deve referenciar um id presente no array.
- **Não invente.** Só inclua conceitos que foram efetivamente cobertos na
  aula. Não preencha lacunas com conhecimento geral do tema.
- **Sem listas, sem markdown nas summaries.** Apenas prosa direta em texto.

## Entrada

Você recebe:
- Título e matéria da aula (contexto)
- Transcrição completa concatenada dos segments

## Saída

JSON estrito conforme schema: `{ "nodes": [...] }`.
""".strip()


_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=str(config("OPENAI_API_KEY")))
    return _openai_client


def _validate_tree_integrity(nodes: list[MindmapNode]) -> bool:
    """Verifica consistência: IDs únicos, parent_ids referenciam IDs existentes, sem ciclos."""
    ids: set[str] = set()
    for node in nodes:
        if node["id"] in ids:
            logger.warning("mindmap_tree_agent emitted duplicate id: %s", node["id"])
            return False
        ids.add(node["id"])

    nodes_by_id: dict[str, MindmapNode] = {node["id"]: node for node in nodes}

    for node in nodes:
        parent = node.get("parent_id")
        if parent is None:
            continue
        if parent not in ids:
            logger.warning("mindmap_tree_agent referenced unknown parent_id: %s", parent)
            return False

    for start in nodes:
        seen: set[str] = set()
        current: MindmapNode | None = start
        while current is not None:
            if current["id"] in seen:
                logger.warning("mindmap_tree_agent emitted cycle around: %s", current["id"])
                return False
            seen.add(current["id"])
            parent_id = current.get("parent_id")
            if parent_id is None:
                break
            current = nodes_by_id.get(parent_id)

    return True


async def build_final_tree(
    full_transcript: str,
    lecture_title: str | None,
    subject_name: str | None,
) -> list[MindmapNode]:
    """Produz a árvore final do mapa mental a partir da transcrição completa.

    Em caso de falha de API ou árvore inconsistente, retorna lista vazia.
    """
    if not full_transcript.strip():
        return []

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
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "mindmap_tree",
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
        logger.exception("mindmap_tree_agent request failed")
        return []

    content = response.choices[0].message.content
    if not content:
        logger.warning("mindmap_tree_agent returned empty content")
        return []

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.exception("mindmap_tree_agent returned invalid JSON")
        return []

    nodes = parsed.get("nodes")
    if not isinstance(nodes, list):
        logger.warning("mindmap_tree_agent returned unexpected shape")
        return []

    if not _validate_tree_integrity(nodes):
        logger.warning("mindmap_tree_agent returned inconsistent tree")
        return []

    return nodes
