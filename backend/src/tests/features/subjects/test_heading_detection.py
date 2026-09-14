from __future__ import annotations

from src.features.subjects.ai.heading_detection import section_text, split_into_sections
from src.features.subjects.ai.text_extraction import Figure, Line

DOC = "Murray - Microbiologia Médica"


def _line(text: str, size: float = 10.0, bold: bool = False, page: int = 1) -> Line:
    return Line(text=text, size=size, bold=bold, page=page)


def _body(quantidade: int = 6, page: int = 1) -> list[Line]:
    return [_line(f"corpo do texto numero {i} com conteudo suficiente", page=page) for i in range(quantidade)]


class TestHeadingPath:
    def test_the_document_name_is_always_the_first_level(self):
        sections = split_into_sections([*_body()], DOC)

        assert len(sections) == 1
        assert sections[0].heading_path == DOC

    def test_levels_stack_from_largest_to_smallest(self):
        elements = [
            _line("CAPÍTULO 1", size=29.0),
            *_body(),
            _line("Mecanismos de Ação", size=16.0),
            *_body(),
            _line("Calor Úmido", size=13.0),
            *_body(),
        ]

        caminhos = [section.heading_path for section in split_into_sections(elements, DOC)]

        assert caminhos == [
            f"{DOC} > CAPÍTULO 1",
            f"{DOC} > CAPÍTULO 1 > Mecanismos de Ação",
            f"{DOC} > CAPÍTULO 1 > Mecanismos de Ação > Calor Úmido",
        ]

    def test_a_higher_level_clears_the_ones_below(self):
        elements = [
            _line("CAPÍTULO 1", size=29.0),
            _line("Mecanismos de Ação", size=16.0),
            *_body(),
            _line("CAPÍTULO 2", size=29.0),
            *_body(),
        ]

        caminhos = [section.heading_path for section in split_into_sections(elements, DOC)]

        assert caminhos[-1] == f"{DOC} > CAPÍTULO 2"


class TestHeadingFilters:
    def test_table_of_contents_lines_are_not_headings(self):
        elements = [
            _line("CAPÍTULO 1.........................................", size=29.0),
            *_body(),
        ]

        assert [s.heading_path for s in split_into_sections(elements, DOC)] == [DOC]

    def test_a_very_long_line_is_not_a_heading(self):
        elements = [_line("x" * 200, size=29.0), *_body()]

        assert [s.heading_path for s in split_into_sections(elements, DOC)] == [DOC]

    def test_at_most_three_levels_are_detected(self):
        elements = [
            _line("Parte Um", size=40.0),
            _line("Capitulo Dois", size=30.0),
            _line("Secao Tres", size=20.0),
            _line("Subsecao Quatro", size=15.0),
            *_body(),
        ]

        caminho = split_into_sections(elements, DOC)[-1].heading_path

        assert caminho.count(">") == 3
        assert "Subsecao Quatro" not in caminho


class TestRepeatedHeadings:
    def test_a_repeated_top_level_heading_is_treated_as_furniture(self):
        elements = []
        for i in range(8):
            elements += [
                _line("Questões para estudo", size=29.0),
                _line(f"Capítulo {i} — Assunto real", size=16.0),
                *_body(),
            ]

        caminhos = {s.heading_path for s in split_into_sections(elements, DOC)}

        assert not any("Questões para estudo" in c for c in caminhos)
        assert f"{DOC} > Capítulo 0 — Assunto real" in caminhos

    def test_a_repeated_deeper_heading_is_kept(self):
        elements = []
        for i in range(8):
            elements += [
                _line(f"Organismo {i}", size=29.0),
                _line("Epidemiologia", size=16.0),
                *_body(),
            ]

        caminhos = {s.heading_path for s in split_into_sections(elements, DOC)}

        assert f"{DOC} > Organismo 3 > Epidemiologia" in caminhos

    def test_a_top_level_heading_below_the_limit_is_kept(self):
        elements = []
        for i in range(3):
            elements += [_line("Parte Recorrente", size=29.0), *_body()]

        caminhos = {s.heading_path for s in split_into_sections(elements, DOC)}

        assert caminhos == {f"{DOC} > Parte Recorrente"}


class TestBoldHeadings:
    def test_bold_at_body_size_fills_the_missing_level(self):
        elements = [
            _line("CAPÍTULO 1", size=17.0),
            *_body(),
            _line("Apresentação", bold=True),
            *_body(),
        ]

        caminho = split_into_sections(elements, DOC)[-1].heading_path

        assert caminho == f"{DOC} > CAPÍTULO 1 > Apresentação"

    def test_a_bold_sentence_is_not_a_heading(self):
        elements = [
            _line("CAPÍTULO 1", size=17.0),
            _line("Esta frase em negrito termina com ponto.", bold=True),
            *_body(),
        ]

        caminho = split_into_sections(elements, DOC)[-1].heading_path

        assert caminho == f"{DOC} > CAPÍTULO 1"


class TestSectionContent:
    def test_pages_come_from_the_elements(self):
        elements = [
            _line("CAPÍTULO 1", size=29.0, page=10),
            *_body(page=11),
            *_body(page=14),
        ]

        section = split_into_sections(elements, DOC)[0]

        assert (section.page_start, section.page_end) == (11, 14)

    def test_the_heading_itself_is_not_part_of_the_body(self):
        elements = [_line("CAPÍTULO 1", size=29.0), *_body()]

        assert "CAPÍTULO 1" not in section_text(split_into_sections(elements, DOC)[0])

    def test_a_figure_caption_is_not_repeated_in_the_body(self):
        legenda = "FIGURA 2-1 Distribuição topográfica"
        elements = [
            *_body(),
            Figure(page=1, bbox=(0, 0, 100, 100), caption=legenda),
            _line(legenda),
        ]

        assert section_text(split_into_sections(elements, DOC)[0]).count(legenda) == 1

    def test_figures_stay_in_the_section_elements(self):
        figura = Figure(page=1, bbox=(0, 0, 100, 100), caption="FIGURA 1-1 Teste")
        elements = [*_body(), figura, *_body()]

        section = split_into_sections(elements, DOC)[0]

        assert figura in section.elements
