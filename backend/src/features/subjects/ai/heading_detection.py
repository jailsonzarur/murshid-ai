from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass

from src.features.subjects.ai.text_extraction import Element, Line

logger = logging.getLogger(__name__)

MAX_LEVELS = 3
MIN_HEADING_CHARS = 3
MAX_HEADING_CHARS = 120
MAX_BOLD_HEADING_CHARS = 80
MIN_LEVEL_SHARE = 0.0005
MAX_TOP_LEVEL_REPEATS = 5

DOTTED_LEADER = re.compile(r"\.{5,}")
PATH_SEPARATOR = " > "


@dataclass(frozen=True)
class Section:
    heading_path: str
    elements: list[Element]
    page_start: int
    page_end: int


def split_into_sections(elements: list[Element], document_title: str) -> list[Section]:
    """Quebra o fluxo em seções pelos títulos detectados. O primeiro nível do
    heading_path é sempre o nome do documento, o que também serve de piso quando
    nenhum título é encontrado."""
    lines = [element for element in elements if isinstance(element, Line)]
    if not lines:
        return []

    body_size = _body_size(lines)
    size_levels = _size_levels(lines, body_size)
    bold_is_heading = _bold_is_heading(lines, body_size, size_levels)

    furniture = _repeated_top_level(lines, size_levels, body_size, bold_is_heading)

    sections: list[Section] = []
    stack: dict[int, str] = {}
    current: list[Element] = []

    def flush() -> None:
        if not current:
            return
        pages = [element.page for element in current]
        sections.append(
            Section(
                heading_path=_path(document_title, stack),
                elements=list(current),
                page_start=min(pages),
                page_end=max(pages),
            )
        )

    for element in elements:
        level = (
            _heading_level(element, size_levels, body_size, bold_is_heading)
            if isinstance(element, Line)
            else None
        )
        if level == 1 and element.text in furniture:
            level = None
        if level is None or not isinstance(element, Line):
            current.append(element)
            continue

        flush()
        current = []
        for deeper in [key for key in stack if key >= level]:
            stack.pop(deeper)
        stack[level] = element.text

    flush()
    return sections


def _repeated_top_level(
    lines: list[Line], size_levels: list[float], body_size: float, bold_is_heading: bool
) -> set[str]:
    """Título de nível 1 que se repete é mobília do livro — "Questões para estudo",
    "Resumo para estudo" — e não capítulo. Como ele zera a pilha, apagaria a
    identidade de tudo abaixo. Níveis mais fundos repetem de forma legítima
    ("Epidemiologia" sob cada organismo), então o filtro só vale no topo."""
    seen: Counter[str] = Counter()
    for line in lines:
        if _heading_level(line, size_levels, body_size, bold_is_heading) == 1:
            seen[line.text] += 1
    return {text for text, total in seen.items() if total > MAX_TOP_LEVEL_REPEATS}


def _body_size(lines: list[Line]) -> float:
    weighted: Counter[float] = Counter()
    for line in lines:
        weighted[line.size] += len(line.text)
    return weighted.most_common(1)[0][0]


def _size_levels(lines: list[Line], body_size: float) -> list[float]:
    weighted: Counter[float] = Counter()
    for line in lines:
        if line.size > body_size:
            weighted[line.size] += len(line.text)

    total = sum(len(line.text) for line in lines)
    candidates = [size for size, volume in weighted.items() if volume / total >= MIN_LEVEL_SHARE]
    return sorted(candidates, reverse=True)[:MAX_LEVELS]


def _bold_is_heading(lines: list[Line], body_size: float, size_levels: list[float]) -> bool:
    if len(size_levels) >= MAX_LEVELS:
        return False
    return any(_is_bold_heading(line, body_size) for line in lines)


def _is_bold_heading(line: Line, body_size: float) -> bool:
    return (
        line.bold
        and line.size == body_size
        and len(line.text) <= MAX_BOLD_HEADING_CHARS
        and not line.text.endswith(".")
    )


def _heading_level(
    line: Line, size_levels: list[float], body_size: float, bold_is_heading: bool
) -> int | None:
    if not _looks_like_heading(line.text):
        return None
    if line.size in size_levels:
        return size_levels.index(line.size) + 1
    if bold_is_heading and _is_bold_heading(line, body_size):
        return len(size_levels) + 1
    return None


def _looks_like_heading(text: str) -> bool:
    return (
        MIN_HEADING_CHARS <= len(text) <= MAX_HEADING_CHARS
        and not DOTTED_LEADER.search(text)
    )


def _path(document_title: str, stack: dict[int, str]) -> str:
    parts = [document_title] + [stack[level] for level in sorted(stack)]
    return PATH_SEPARATOR.join(parts)


def section_text(section: Section) -> str:
    """Só as linhas. A legenda da figura já está entre elas como texto da página;
    o campo caption existe para exibir junto da imagem, não para repetir aqui."""
    return "\n".join(
        element.text for element in section.elements if isinstance(element, Line)
    )
