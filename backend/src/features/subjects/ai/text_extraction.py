from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

MIN_IMAGE_SIDE = 60.0
MAX_PAGE_COVERAGE = 0.8
CAPTION_MAX_GAP = 60.0
CAPTION_PATTERN = re.compile(r"^\s*(figuras?|fig\.|tabelas?|quadros?|box|gr[áa]fico)\s*[\d IVXivx]", re.I)

_BOLD_FLAG = 1 << 4


@dataclass(frozen=True)
class Line:
    text: str
    size: float
    bold: bool
    page: int


@dataclass(frozen=True)
class Figure:
    page: int
    bbox: tuple[float, float, float, float]
    caption: str | None


Element = Line | Figure


def extract_elements(source_path: Path) -> list[Element]:
    """Texto e imagens num único fluxo, na ordem de leitura. É essa ordem que
    permite o chunker saber em qual chunk cada figura caiu."""
    import pymupdf

    elements: list[Element] = []

    with pymupdf.open(str(source_path)) as document:
        for index in range(document.page_count):
            page = document[index]
            raw = cast(dict[str, Any], page.get_text("dict"))
            blocks = cast(list[dict[str, Any]], raw["blocks"])
            text_blocks = [block for block in blocks if block["type"] == 0]
            page_area = page.rect.width * page.rect.height
            elements.extend(_page_elements(blocks, text_blocks, index + 1, page_area))

    return elements


def _page_elements(
    blocks: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
    page: int,
    page_area: float,
) -> list[Element]:
    ordered = sorted(blocks, key=lambda block: (round(block["bbox"][1], 1), block["bbox"][0]))
    elements: list[Element] = []

    for block in ordered:
        if block["type"] == 1:
            figure = _figure(block, text_blocks, page, page_area)
            if figure is not None:
                elements.append(figure)
            continue

        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(span["text"] for span in spans).strip()
            if not text:
                continue
            first = spans[0]
            elements.append(
                Line(
                    text=text,
                    size=round(first["size"], 1),
                    bold=bool(first["flags"] & _BOLD_FLAG),
                    page=page,
                )
            )

    return elements


def _figure(
    block: dict[str, Any], text_blocks: list[dict[str, Any]], page: int, page_area: float
) -> Figure | None:
    x0, y0, x1, y1 = block["bbox"]
    width, height = x1 - x0, y1 - y0
    if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
        return None
    if page_area and (width * height) / page_area > MAX_PAGE_COVERAGE:
        return None
    return Figure(page=page, bbox=(x0, y0, x1, y1), caption=_caption(block["bbox"], text_blocks))


def _caption(image_bbox: tuple[float, ...], text_blocks: list[dict[str, Any]]) -> str | None:
    ix0, _, ix1, iy1 = image_bbox

    for block in text_blocks:
        tx0, ty0, tx1, _ = block["bbox"]
        if ty0 < iy1 - 5 or ty0 - iy1 > CAPTION_MAX_GAP:
            continue
        if tx0 >= ix1 or tx1 <= ix0:
            continue
        text = " ".join(
            "".join(span["text"] for span in line.get("spans", []))
            for line in block.get("lines", [])
        ).strip()
        if CAPTION_PATTERN.match(text):
            return text

    return None
