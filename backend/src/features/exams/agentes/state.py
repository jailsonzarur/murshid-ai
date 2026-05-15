from __future__ import annotations

from typing import Required, TypedDict
from uuid import UUID

from src.features.exams.schemas.exam_schemas import ExamExtractionSchema, RawExamExtractionSchema


class OriginalDocumentState(TypedDict, total=False):
    file_url: str
    url: str
    key: str
    original_name: str
    mime_type: str
    page_order: int


class LayoutElementState(TypedDict):
    page_index: int
    coordinates: tuple[float, float, float, float]


class QuestionStartState(TypedDict):
    question_number: int
    page_index: int
    y: float
    text: str


class VisualBoxState(TypedDict):
    box_id: int
    page_index: int
    coordinates: tuple[float, float, float, float]


class ExamProcessingState(TypedDict, total=False):
    exam_id: Required[UUID]
    original_docs: list[OriginalDocumentState]
    layout_elements: dict[int, LayoutElementState]
    annotated_pages_base64: list[str]
    original_pages_base64: list[str]
    question_boundary_hints: list[str]
    raw_extracted_data: RawExamExtractionSchema
    extracted_data: ExamExtractionSchema
