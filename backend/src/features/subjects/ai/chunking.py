from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from src.features.subjects.ai.heading_detection import Section
from src.features.subjects.ai.text_extraction import Figure, Line

logger = logging.getLogger(__name__)

TARGET_CHARS = 1600
OVERLAP_CHARS = 150
MIN_TAIL_CHARS = 400
CAPTION_MARGIN = 40

SENTENCE_END = re.compile(r"(?<=[.!?])\s")


@dataclass(frozen=True)
class Chunk:
    text: str
    heading_path: str
    page_start: int
    page_end: int
    figures: list[Figure]


def chunk_sections(sections: list[Section]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in sections:
        chunks.extend(_chunk_section(section))
    return chunks


def _chunk_section(section: Section) -> list[Chunk]:
    text, figures_at, pages_at = _layout(section)
    if not text.strip():
        return []

    guards = [(offset, offset + len(figure.caption) + CAPTION_MARGIN) for offset, figure in figures_at]

    return [
        Chunk(
            text=text[start:end].strip(),
            heading_path=section.heading_path,
            page_start=_page_at(pages_at, start, section.page_start),
            page_end=_page_at(pages_at, max(start, end - 1), section.page_end),
            figures=[figure for offset, figure in figures_at if start <= offset < end],
        )
        for start, end in _spans(text, guards)
        if text[start:end].strip()
    ]


def _layout(section: Section) -> tuple[str, list[tuple[int, Figure]], list[tuple[int, int]]]:
    parts: list[str] = []
    figures_at: list[tuple[int, Figure]] = []
    pages_at: list[tuple[int, int]] = []
    offset = 0

    for element in section.elements:
        if isinstance(element, Figure):
            figures_at.append((offset, element))
            continue
        if isinstance(element, Line):
            pages_at.append((offset, element.page))
            parts.append(element.text)
            offset += len(element.text) + 1

    return "\n".join(parts), figures_at, pages_at


def _spans(text: str, guards: list[tuple[int, int]]) -> list[tuple[int, int]]:
    total = len(text)
    if total <= TARGET_CHARS:
        return [(0, total)]

    boundaries = [match.start() for match in SENTENCE_END.finditer(text)]
    spans: list[tuple[int, int]] = []
    start = 0

    while start < total:
        end = _cut(start, boundaries, guards, total)
        spans.append((start, end))
        if end >= total:
            break
        start = max(end - OVERLAP_CHARS, start + 1)

    return spans


def _cut(
    start: int, boundaries: list[int], guards: list[tuple[int, int]], total: int
) -> int:
    limit = start + TARGET_CHARS
    if total - limit < MIN_TAIL_CHARS:
        return total

    candidates = [end for end in boundaries if start + MIN_TAIL_CHARS < end <= limit]
    end = candidates[-1] if candidates else limit
    return _clear_of_captions(end, guards, total)


def _clear_of_captions(end: int, guards: list[tuple[int, int]], total: int) -> int:
    for guard_start, guard_end in guards:
        if guard_start < end < guard_end:
            return min(guard_end, total)
    return end


def _page_at(pages_at: list[tuple[int, int]], offset: int, fallback: int) -> int:
    page = fallback
    for line_offset, line_page in pages_at:
        if line_offset > offset:
            break
        page = line_page
    return page
