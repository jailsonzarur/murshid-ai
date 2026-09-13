from __future__ import annotations

import pytest

from src.features.subjects.ai.text_extraction import (
    Figure,
    Line,
    _caption,
    _page_elements,
)

PAGE_AREA = 600.0 * 800.0


def _span(text: str, size: float = 10.0, bold: bool = False) -> dict:
    return {"text": text, "size": size, "flags": (1 << 4) if bold else 0}


def _text_block(text: str, bbox: tuple[float, ...], size: float = 10.0, bold: bool = False) -> dict:
    return {
        "type": 0,
        "bbox": bbox,
        "lines": [{"spans": [_span(text, size, bold)]}],
    }


def _image_block(bbox: tuple[float, ...]) -> dict:
    return {"type": 1, "bbox": bbox}


class TestReadingOrder:
    def test_blocks_come_out_top_to_bottom(self):
        blocks = [
            _text_block("segundo", (0, 200, 300, 220)),
            _text_block("primeiro", (0, 100, 300, 120)),
        ]
        elements = _page_elements(blocks, blocks, page=1, page_area=PAGE_AREA)

        assert [element.text for element in elements] == ["primeiro", "segundo"]

    def test_a_figure_sits_between_the_text_around_it(self):
        antes = _text_block("corpo antes", (0, 50, 300, 70))
        imagem = _image_block((0, 100, 260, 400))
        legenda = _text_block("FIGURA 2-1 Parede celular", (0, 410, 300, 430))
        blocks = [antes, imagem, legenda]

        elements = _page_elements(blocks, [antes, legenda], page=7, page_area=PAGE_AREA)

        assert isinstance(elements[0], Line)
        assert isinstance(elements[1], Figure)
        assert isinstance(elements[2], Line)
        assert elements[1].page == 7


class TestLines:
    def test_the_size_and_weight_come_from_the_line(self):
        blocks = [_text_block("CAPÍTULO 1", (0, 10, 300, 40), size=29.0, bold=True)]

        line = _page_elements(blocks, blocks, page=1, page_area=PAGE_AREA)[0]

        assert isinstance(line, Line)
        assert (line.size, line.bold) == (29.0, True)

    def test_blank_lines_are_dropped(self):
        blocks = [_text_block("   ", (0, 10, 300, 40))]

        assert _page_elements(blocks, blocks, page=1, page_area=PAGE_AREA) == []


class TestFigureFiltering:
    def test_tiny_images_are_ignored(self):
        blocks = [_image_block((0, 0, 40, 40))]

        assert _page_elements(blocks, [], page=1, page_area=PAGE_AREA) == []

    def test_a_full_page_scan_is_not_a_figure(self):
        blocks = [_image_block((0, 0, 600, 800))]

        assert _page_elements(blocks, [], page=1, page_area=PAGE_AREA) == []

    def test_a_figure_sized_image_with_a_caption_is_kept(self):
        imagem = _image_block((50, 50, 400, 500))
        legenda = _text_block("FIGURA 3-2 Ciclo de vida", (50, 510, 400, 530))

        elements = _page_elements([imagem, legenda], [legenda], page=1, page_area=PAGE_AREA)

        assert isinstance(elements[0], Figure)
        assert elements[0].caption == "FIGURA 3-2 Ciclo de vida"

    def test_an_image_without_a_caption_is_dropped(self):
        blocks = [_image_block((50, 50, 400, 500))]

        assert _page_elements(blocks, [], page=1, page_area=PAGE_AREA) == []


class TestCaption:
    @pytest.mark.parametrize(
        "texto",
        [
            "FIGURA 2-1 Distribuição topográfica",
            "Figura 12 Estrutura",
            "Tabela 3 Comparação",
            "Quadro 1 Resumo",
            "Gráfico 4 Evolução",
        ],
    )
    def test_recognises_the_usual_labels(self, texto):
        imagem = (0.0, 100.0, 260.0, 400.0)
        blocks = [_text_block(texto, (0, 410, 300, 430))]

        assert _caption(imagem, blocks) == texto

    def test_ignores_text_that_is_not_a_caption(self):
        imagem = (0.0, 100.0, 260.0, 400.0)
        blocks = [_text_block("Como em outros tecidos, o microbioma", (0, 410, 300, 430))]

        assert _caption(imagem, blocks) is None

    def test_ignores_text_too_far_below_the_image(self):
        imagem = (0.0, 100.0, 260.0, 400.0)
        blocks = [_text_block("FIGURA 2-1 Longe demais", (0, 900, 300, 920))]

        assert _caption(imagem, blocks) is None

    def test_ignores_text_in_another_column(self):
        imagem = (0.0, 100.0, 260.0, 400.0)
        blocks = [_text_block("FIGURA 9-9 Outra coluna", (300, 410, 580, 430))]

        assert _caption(imagem, blocks) is None
