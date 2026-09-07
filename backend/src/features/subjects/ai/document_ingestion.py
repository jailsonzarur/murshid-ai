from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

THUMBNAIL_ZOOM = 2.0
THUMBNAIL_MAX_WIDTH = 720
ICON_SIZE = 128


@dataclass(frozen=True)
class DocumentPreview:
    page_count: int | None
    thumbnail_png: bytes | None
    icon_png: bytes | None


def build_preview(source_path: Path, mime_type: str) -> DocumentPreview:
    """Renderiza a capa e conta as páginas. Só PDF tem capa; o resto passa direto."""
    if mime_type != "application/pdf" and source_path.suffix.lower() != ".pdf":
        return DocumentPreview(page_count=None, thumbnail_png=None, icon_png=None)

    import pymupdf

    with pymupdf.open(str(source_path)) as document:
        page_count = document.page_count
        if page_count == 0:
            return DocumentPreview(page_count=0, thumbnail_png=None, icon_png=None)

        page = document[0]
        zoom = THUMBNAIL_ZOOM
        width = page.rect.width * zoom
        if width > THUMBNAIL_MAX_WIDTH:
            zoom = THUMBNAIL_MAX_WIDTH / page.rect.width

        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)

        return DocumentPreview(
            page_count=page_count,
            thumbnail_png=pixmap.tobytes("png"),
            icon_png=_render_square_icon(page, pymupdf),
        )


def _render_square_icon(page: Any, pymupdf: Any) -> bytes:
    """Recorta o topo da página num quadrado. Renderizar já cortado evita baixar
    a altura inteira de uma capa em retrato para exibir 40px."""
    rect = page.rect
    side = min(rect.width, rect.height)
    clip = pymupdf.Rect(rect.x0, rect.y0, rect.x0 + side, rect.y0 + side)
    zoom = ICON_SIZE / side
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
    return pixmap.tobytes("png")
