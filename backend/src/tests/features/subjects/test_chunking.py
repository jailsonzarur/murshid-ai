from __future__ import annotations

from src.features.subjects.ai.chunking import (
    OVERLAP_CHARS,
    TARGET_CHARS,
    Chunk,
    chunk_sections,
)
from src.features.subjects.ai.heading_detection import Section
from src.features.subjects.ai.text_extraction import Element, Figure, Line

CAMINHO = "Murray > Bactérias > Parede Celular"


def _line(text: str, page: int = 1) -> Line:
    return Line(text=text, size=10.0, bold=False, page=page)


def _section(elements: list[Element], heading_path: str = CAMINHO) -> Section:
    pages = [element.page for element in elements]
    return Section(
        heading_path=heading_path,
        elements=elements,
        page_start=min(pages),
        page_end=max(pages),
    )


def _frases(quantidade: int, page: int = 1) -> list[Line]:
    return [
        _line(f"Esta e a frase numero {i} com conteudo suficiente para ocupar espaco.", page)
        for i in range(quantidade)
    ]


class TestSmallSections:
    def test_a_section_that_fits_becomes_one_chunk(self):
        chunks = chunk_sections([_section(_frases(3))])

        assert len(chunks) == 1
        assert chunks[0].heading_path == CAMINHO

    def test_an_empty_section_produces_nothing(self):
        assert chunk_sections([_section([_line("   ")])]) == []

    def test_the_heading_is_carried_to_every_chunk(self):
        chunks = chunk_sections([_section(_frases(120))])

        assert len(chunks) > 1
        assert {chunk.heading_path for chunk in chunks} == {CAMINHO}


class TestSplitting:
    def test_a_long_section_is_split(self):
        chunks = chunk_sections([_section(_frases(200))])

        assert len(chunks) > 1

    def test_chunks_stay_near_the_target(self):
        chunks = chunk_sections([_section(_frases(200))])

        assert all(len(chunk.text) <= TARGET_CHARS * 2 for chunk in chunks)

    def test_the_split_never_crosses_a_section(self):
        primeira = _section(_frases(120), "Doc > Uma")
        segunda = _section(_frases(120), "Doc > Outra")

        chunks = chunk_sections([primeira, segunda])

        for chunk in chunks:
            assert chunk.heading_path in {"Doc > Uma", "Doc > Outra"}

    def test_consecutive_chunks_overlap(self):
        chunks = chunk_sections([_section(_frases(200))])

        primeiro, segundo = chunks[0], chunks[1]
        assert primeiro.text[-OVERLAP_CHARS // 2 :] in " ".join([primeiro.text, segundo.text])


class TestPages:
    def test_the_page_range_follows_the_lines(self):
        elements = [*_frases(3, page=10), *_frases(3, page=11)]

        chunk = chunk_sections([_section(elements)])[0]

        assert (chunk.page_start, chunk.page_end) == (10, 11)


class TestFigures:
    def test_a_figure_lands_in_the_chunk_it_sits_in(self):
        figura = Figure(page=1, bbox=(0, 0, 100, 100), caption="FIGURA 1-1 Parede")
        elements: list[Element] = [*_frases(2), figura, _line("FIGURA 1-1 Parede"), *_frases(2)]

        chunks = chunk_sections([_section(elements)])

        assert len(chunks) == 1
        assert chunks[0].figures == [figura]

    def test_a_chunk_can_hold_more_than_one_figure(self):
        uma = Figure(page=1, bbox=(0, 0, 100, 100), caption="FIGURA 1-1 Uma")
        outra = Figure(page=1, bbox=(0, 0, 100, 100), caption="FIGURA 1-2 Outra")
        elements: list[Element] = [
            *_frases(2),
            uma,
            _line("FIGURA 1-1 Uma"),
            outra,
            _line("FIGURA 1-2 Outra"),
        ]

        chunks = chunk_sections([_section(elements)])

        assert chunks[0].figures == [uma, outra]

    def test_a_figure_is_never_split_from_its_caption(self):
        legenda = "FIGURA 9-9 " + "descricao extensa da figura " * 6
        elements: list[Element] = [
            *_frases(30),
            Figure(page=1, bbox=(0, 0, 100, 100), caption=legenda),
            _line(legenda),
            *_frases(30),
        ]

        chunks = chunk_sections([_section(elements)])

        for chunk in chunks:
            if chunk.figures:
                assert legenda in chunk.text

    def test_a_section_without_figures_reports_none(self):
        chunk = chunk_sections([_section(_frases(3))])[0]

        assert chunk.figures == []


class TestChunkShape:
    def test_the_text_is_stripped(self):
        chunks: list[Chunk] = chunk_sections([_section([_line("  com espacos  ")])])

        assert chunks[0].text == "com espacos"
