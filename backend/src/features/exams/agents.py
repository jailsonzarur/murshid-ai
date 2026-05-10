from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import shutil
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Required, TypedDict, TypeVar, cast
from uuid import UUID

from decouple import config
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import AsyncSessionLocal
from src.features.categories.models import CategoryModel
from src.features.exams.schemas.exam_schemas import (
    ExamExtractionSchema,
    QuestionSchema,
    RawExamExtractionSchema,
    RawQuestionSchema,
)
from src.features.files.services.bucket_service import MinioBucketService, get_bucket_service
from src.features.questions.models import OptionModel, QuestionModel, QuestionType

logger = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)

VISION_EXTRACTION_PROMPT = """
Extract the exam questions into raw text blocks. I have drawn red boxes with numeric IDs over non-text elements.
RULES:

TEXT EXTRACTION: Extract all printed text for a question (including its options, if any) into a single
raw_text string. IGNORE handwriting, circles, or scribbles.

IMAGE SPLITS: If an image visually splits a question's text, merge all the text into the same raw_text until
the next numbered question begins.

QUESTION BOUNDARIES: A question remains active until the next numbered question begins. A page break does NOT
end the current question.

CROSS-PAGE CONTINUATION: If a page starts with an image, table, graph, or diagram before any new numbered question
appears on that page, associate that red box with the previous question from the previous page.

BOX IDs: If the question refers to or contains red boxes, list their IDs in box_ids. Group them if they belong
to the same figure (e.g., [1, 2]).
""".strip()

TEXT_STRUCTURING_PROMPT = """
You are an expert in educational data structuring. Your task is to parse the following raw exam question text
into a structured format.
Separate the main statement from its options (if they exist).

Follow these BUSINESS RULES to determine the type:

CATEGORY 1: OBJECTIVE

Classic Multiple Choice: The question has options (a, b, c, d), and the user must select the single correct one.

Multiple Choice (True/False / Multi-select): The question has options, but multiple can be correct or the user
must judge each as True/False.

CATEGORY 2: SUBJECTIVE

Single Essay: The question is purely a statement asking for an explanation. There are NO options. (Set options to
an empty list).

Multi-item Essay: The question has a main statement and sub-items (e.g., a) Explain X, b) Explain Y) where the
user must write a text response for each item. Parse these sub-items into the options list.

Ensure the box_ids and exam_order are preserved exactly as provided in the input.
""".strip()

VISUAL_ELEMENT_CATEGORIES = {"Image", "Figure", "Table"}
QUESTION_START_PATTERN = re.compile(
    r"^\s*(?:quest(?:ão|ao)?\s*)?(\d{1,3})(?:\s*[\.\-–:]|\s*$)",
    re.IGNORECASE,
)


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


async def process_layout_node(state: ExamProcessingState) -> ExamProcessingState:
    exam_id = state["exam_id"]
    bucket_service = get_bucket_service()
    layout_elements = dict(state.get("layout_elements", {}))
    annotated_pages_base64 = list(state.get("annotated_pages_base64", []))
    original_pages_base64 = list(state.get("original_pages_base64", []))
    question_starts: list[QuestionStartState] = []
    visual_boxes: list[VisualBoxState] = []
    box_id_counter = max(layout_elements.keys(), default=0) + 1

    with TemporaryDirectory(prefix=f"exam-layout-{exam_id}-") as temp_dir:
        temp_path = Path(temp_dir)
        global_page_offset = len(original_pages_base64)

        for document_index, document in enumerate(_sorted_documents(state.get("original_docs", [])), start=1):
            document_path = _download_document(bucket_service, document, temp_path, document_index)
            clean_pages = _document_to_pil_pages(document_path, document.get("mime_type"))
            elements = await asyncio.to_thread(_partition_document, document_path)
            visual_boxes_by_page = _get_visual_boxes_by_page(elements, clean_pages)
            question_starts.extend(_get_question_starts(elements, clean_pages, global_page_offset))

            for local_page_index, clean_page in enumerate(clean_pages):
                global_page_index = global_page_offset + local_page_index
                original_pages_base64.append(_pil_image_to_jpeg_base64(clean_page))

                annotated_page = clean_page.copy()
                for coordinates in visual_boxes_by_page.get(local_page_index, []):
                    box_id = box_id_counter
                    _draw_numbered_box(annotated_page, coordinates, box_id)
                    layout_elements[box_id] = {
                        "page_index": global_page_index,
                        "coordinates": coordinates,
                    }
                    visual_boxes.append(
                        {
                            "box_id": box_id,
                            "page_index": global_page_index,
                            "coordinates": coordinates,
                        }
                    )
                    box_id_counter += 1

                _save_debug_annotated_page(annotated_page, exam_id, global_page_index)
                annotated_pages_base64.append(_pil_image_to_jpeg_base64(annotated_page))

            global_page_offset += len(clean_pages)

    question_boundary_hints = _build_question_boundary_hints(question_starts, visual_boxes)
    _save_debug_question_boundary_hints(question_boundary_hints, exam_id)

    return {
        **state,
        "layout_elements": layout_elements,
        "annotated_pages_base64": annotated_pages_base64,
        "original_pages_base64": original_pages_base64,
        "question_boundary_hints": question_boundary_hints,
    }


async def vision_extraction_node(state: ExamProcessingState) -> ExamProcessingState:
    from langchain_core.messages import HumanMessage

    content: list[dict[str, Any]] = [{"type": "text", "text": VISION_EXTRACTION_PROMPT}]
    question_boundary_hints = state.get("question_boundary_hints", [])
    if question_boundary_hints:
        content.append({"type": "text", "text": _format_question_boundary_hints(question_boundary_hints)})

    for page_index, page_base64 in enumerate(state.get("annotated_pages_base64", []), start=1):
        content.append({"type": "text", "text": f"Annotated page {page_index}"})
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": _build_data_url(page_base64, "image/jpeg")},
            }
        )

    llm = _get_vision_llm().with_structured_output(RawExamExtractionSchema)
    raw_extracted_data = await _invoke_structured_llm(
        llm,
        [HumanMessage(content=cast(Any, content))],
        RawExamExtractionSchema,
    )
    _save_debug_vision_output(raw_extracted_data, state["exam_id"])

    return {**state, "raw_extracted_data": raw_extracted_data}


async def text_structuring_node(state: ExamProcessingState) -> ExamProcessingState:
    raw_extracted_data = state.get("raw_extracted_data")
    if raw_extracted_data is None:
        raise ValueError("No raw extracted data available to structure")

    llm = _get_text_structuring_llm().with_structured_output(QuestionSchema)
    questions: list[QuestionSchema] = []

    for raw_question in raw_extracted_data.questions:
        parsed_question = await _structure_raw_question(llm, raw_question)
        questions.append(parsed_question)

    extracted_data = ExamExtractionSchema(questions=questions)

    return {**state, "extracted_data": extracted_data}


async def _structure_raw_question(llm: Any, raw_question: RawQuestionSchema) -> QuestionSchema:
    from langchain_core.messages import HumanMessage

    raw_payload = json.dumps(raw_question.model_dump(mode="json"), ensure_ascii=False, indent=2)
    message = (
        f"{TEXT_STRUCTURING_PROMPT}\n\n"
        "RAW QUESTION INPUT:\n"
        f"{raw_payload}\n\n"
        "The output schema requires `category_name`; infer a concise category from the question subject. "
        'Use "Uncategorized" if unclear.'
    )
    parsed_question = await _invoke_structured_llm(
        llm,
        [HumanMessage(content=message)],
        QuestionSchema,
    )

    return parsed_question.model_copy(
        update={
            "box_ids": list(raw_question.box_ids),
            "exam_order": raw_question.exam_order,
        }
    )


async def save_results_node(state: ExamProcessingState) -> ExamProcessingState:
    extracted_data = state.get("extracted_data")
    if extracted_data is None:
        raise ValueError("No extracted data available to save")

    bucket_service = get_bucket_service()

    async with AsyncSessionLocal() as db:
        try:
            await _delete_existing_questions(db, state["exam_id"])

            category_cache: dict[str, CategoryModel] = {}
            for question in extracted_data.questions:
                category = await _get_or_create_category(db, category_cache, question.category_name)
                image_url = _crop_and_upload_question_image(
                    bucket_service=bucket_service,
                    state=state,
                    box_ids=question.box_ids,
                    exam_order=question.exam_order,
                )
                question_model = QuestionModel(
                    exam_id=state["exam_id"],
                    category_id=category.id,
                    type=QuestionType(question.type),
                    statement=question.statement,
                    image_url=image_url,
                    justification=None,
                    exam_order=question.exam_order,
                )

                for option in question.options:
                    question_model.options.append(
                        OptionModel(
                            text=option.text,
                            letter=option.letter,
                            is_correct=option.is_correct,
                        )
                    )

                db.add(question_model)

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return state


def build_exam_processing_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(ExamProcessingState)
    graph.add_node("process_layout_node", process_layout_node)
    graph.add_node("vision_extraction_node", vision_extraction_node)
    graph.add_node("text_structuring_node", text_structuring_node)
    graph.add_node("save_results_node", save_results_node)

    graph.add_edge(START, "process_layout_node")
    graph.add_edge("process_layout_node", "vision_extraction_node")
    graph.add_edge("vision_extraction_node", "text_structuring_node")
    graph.add_edge("text_structuring_node", "save_results_node")
    graph.add_edge("save_results_node", END)

    return graph.compile()


async def run_exam_processing_graph(initial_state: ExamProcessingState) -> ExamProcessingState:
    graph = build_exam_processing_graph()
    result = await graph.ainvoke(initial_state)
    return cast(ExamProcessingState, result)


def _partition_document(document_path: Path) -> list[Any]:
    from unstructured.partition.auto import partition

    _ensure_tesseract_available()

    return partition(
        filename=str(document_path),
        strategy="hi_res",
        languages=_get_ocr_languages(),
        pdf_infer_table_structure=True,
    )


def _ensure_tesseract_available() -> None:
    if shutil.which("tesseract"):
        return

    raise RuntimeError(
        "Tesseract OCR is required by unstructured hi_res layout extraction, but the `tesseract` binary was not found "
        "in PATH. Install it locally with `brew install tesseract` before running the Celery worker on macOS. If you "
        "need Portuguese OCR data, also install `brew install tesseract-lang` and set EXAM_OCR_LANGUAGES=por,eng."
    )


def _get_ocr_languages() -> list[str]:
    raw_languages = str(config("EXAM_OCR_LANGUAGES", default="eng"))
    languages = [language.strip() for language in raw_languages.split(",") if language.strip()]
    return languages or ["eng"]


def _get_question_starts(
    elements: list[Any],
    page_images: list[Any],
    global_page_offset: int,
) -> list[QuestionStartState]:
    question_starts: list[QuestionStartState] = []

    for element in elements:
        question_number = _extract_question_number(_get_element_text(element))
        if question_number is None:
            continue

        metadata = getattr(element, "metadata", None)
        page_number = int(getattr(metadata, "page_number", 1) or 1)
        local_page_index = page_number - 1

        if local_page_index < 0 or local_page_index >= len(page_images):
            continue

        box = _extract_element_box(element, page_images[local_page_index])
        question_starts.append(
            {
                "question_number": question_number,
                "page_index": global_page_offset + local_page_index,
                "y": box[1] if box else 0,
                "text": _get_element_text(element)[:180],
            }
        )

    return _dedupe_question_starts(question_starts)


def _extract_question_number(text: str) -> int | None:
    for line in text.splitlines():
        normalized_line = line.strip()
        if not normalized_line:
            continue

        match = QUESTION_START_PATTERN.match(normalized_line)
        if not match:
            continue

        question_number = int(match.group(1))
        if 0 < question_number <= 300:
            return question_number

    return None


def _get_element_text(element: Any) -> str:
    text = getattr(element, "text", None)
    if text:
        return str(text).strip()

    return str(element).strip()


def _dedupe_question_starts(question_starts: list[QuestionStartState]) -> list[QuestionStartState]:
    sorted_starts = sorted(question_starts, key=lambda item: (item["page_index"], item["y"], item["question_number"]))
    deduped: list[QuestionStartState] = []
    seen_numbers: set[int] = set()

    for question_start in sorted_starts:
        question_number = question_start["question_number"]
        if question_number in seen_numbers:
            continue

        seen_numbers.add(question_number)
        deduped.append(question_start)

    return deduped


def _build_question_boundary_hints(
    question_starts: list[QuestionStartState],
    visual_boxes: list[VisualBoxState],
) -> list[str]:
    sorted_starts = sorted(question_starts, key=lambda item: (item["page_index"], item["y"], item["question_number"]))
    sorted_boxes = sorted(visual_boxes, key=lambda item: (item["page_index"], item["coordinates"][1], item["box_id"]))
    hints: list[str] = []

    for index, question_start in enumerate(sorted_starts):
        next_question_start = sorted_starts[index + 1] if index + 1 < len(sorted_starts) else None
        candidate_boxes = [
            visual_box
            for visual_box in sorted_boxes
            if _is_box_inside_question_span(visual_box, question_start, next_question_start)
        ]
        candidate_box_ids = [visual_box["box_id"] for visual_box in candidate_boxes]

        if not candidate_box_ids:
            continue

        hints.append(_format_question_span_hint(question_start, next_question_start, candidate_boxes))

    return hints


def _is_box_inside_question_span(
    visual_box: VisualBoxState,
    question_start: QuestionStartState,
    next_question_start: QuestionStartState | None,
) -> bool:
    box_position = (visual_box["page_index"], visual_box["coordinates"][1])
    start_position = (question_start["page_index"], question_start["y"])

    if box_position < start_position:
        return False

    if next_question_start is None:
        return True

    next_start_position = (next_question_start["page_index"], next_question_start["y"])
    return box_position < next_start_position


def _format_question_span_hint(
    question_start: QuestionStartState,
    next_question_start: QuestionStartState | None,
    candidate_boxes: list[VisualBoxState],
) -> str:
    candidate_box_ids = [visual_box["box_id"] for visual_box in candidate_boxes]
    page_number = question_start["page_index"] + 1
    boundary = "the end of the document"
    cross_page_box_ids = [
        visual_box["box_id"]
        for visual_box in candidate_boxes
        if visual_box["page_index"] > question_start["page_index"]
    ]

    if next_question_start is not None:
        boundary = (
            f"Question {next_question_start['question_number']} starts on annotated page "
            f"{next_question_start['page_index'] + 1} near y={round(next_question_start['y'])}"
        )

    hint = (
        f"Question {question_start['question_number']} starts on annotated page {page_number} "
        f"near y={round(question_start['y'])} and continues until {boundary}. "
        f"Candidate red boxes inside this question span: {candidate_box_ids}."
    )

    if cross_page_box_ids:
        hint += (
            f" Cross-page continuation boxes before the next question boundary: {cross_page_box_ids}; "
            f"prefer assigning them to Question {question_start['question_number']} unless the printed text clearly "
            "states otherwise."
        )

    return hint


def _format_question_boundary_hints(question_boundary_hints: list[str]) -> str:
    formatted_hints = "\n".join(f"- {hint}" for hint in question_boundary_hints)
    return (
        "QUESTION BOUNDARY HINTS FROM OCR/LAYOUT PREPROCESSING:\n"
        "Use these hints to associate red box IDs with the correct question. These hints are derived from detected "
        "question-number positions and should override simple visual proximity when a page break occurs.\n"
        f"{formatted_hints}"
    )


def _save_debug_question_boundary_hints(question_boundary_hints: list[str], exam_id: UUID) -> None:
    if not config("EXAM_VISION_DEBUG_ENABLED", default=True, cast=bool):
        return

    try:
        debug_dir = _get_vision_debug_dir() / str(exam_id)
        debug_dir.mkdir(parents=True, exist_ok=True)
        output_path = debug_dir / "question-boundary-hints.json"
        output_path.write_text(
            json.dumps({"hints": question_boundary_hints}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved question boundary debug hints: %s", output_path)
    except OSError:
        logger.exception("Failed to save question boundary debug hints for exam %s", exam_id)


def _save_debug_annotated_page(image: Any, exam_id: UUID, page_index: int) -> None:
    if not config("EXAM_LAYOUT_DEBUG_ENABLED", default=True, cast=bool):
        return

    try:
        debug_dir = _get_layout_debug_dir() / str(exam_id)
        debug_dir.mkdir(parents=True, exist_ok=True)
        output_path = debug_dir / f"annotated-page-{page_index + 1}.jpg"
        image.convert("RGB").save(output_path, format="JPEG", quality=95)
        logger.info("Saved annotated layout debug image: %s", output_path)
    except OSError:
        logger.exception("Failed to save annotated layout debug image for exam %s page %s", exam_id, page_index + 1)


def _get_layout_debug_dir() -> Path:
    raw_path = str(config("EXAM_LAYOUT_DEBUG_DIR", default="tmp/exam-layout-debug")).strip()
    debug_path = Path(raw_path).expanduser()

    if debug_path.is_absolute():
        return debug_path

    return _get_api_root_dir() / debug_path


def _get_api_root_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def _save_debug_vision_output(raw_extracted_data: RawExamExtractionSchema, exam_id: UUID) -> None:
    if not config("EXAM_VISION_DEBUG_ENABLED", default=True, cast=bool):
        return

    try:
        debug_dir = _get_vision_debug_dir() / str(exam_id)
        debug_dir.mkdir(parents=True, exist_ok=True)
        output_path = debug_dir / "vision-output.json"
        output_path.write_text(
            json.dumps(raw_extracted_data.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved vision extraction debug output: %s", output_path)
    except OSError:
        logger.exception("Failed to save vision extraction debug output for exam %s", exam_id)


def _get_vision_debug_dir() -> Path:
    raw_path = str(config("EXAM_VISION_DEBUG_DIR", default="/tmp/exam-vision-debug")).strip()
    return Path(raw_path).expanduser()


def _get_vision_llm():
    from langchain_openai import ChatOpenAI

    model_name = str(config("EXAM_VISION_MODEL", default=config("OPENAI_VISION_MODEL", default="gpt-4o")))
    api_key = str(config("OPENAI_API_KEY", default="")).strip()
    kwargs: dict[str, Any] = {"model": model_name, "temperature": 0}

    if api_key:
        kwargs["api_key"] = api_key

    return ChatOpenAI(**kwargs)


def _get_text_structuring_llm():
    from langchain_openai import ChatOpenAI

    model_name = str(config("EXAM_TEXT_MODEL", default=config("OPENAI_TEXT_MODEL", default="gpt-4o")))
    api_key = str(config("OPENAI_API_KEY", default="")).strip()
    kwargs: dict[str, Any] = {"model": model_name, "temperature": 0}

    if api_key:
        kwargs["api_key"] = api_key

    return ChatOpenAI(**kwargs)


async def _invoke_structured_llm(
    llm: Any,
    messages: list[Any],
    schema: type[SchemaT],
) -> SchemaT:
    if hasattr(llm, "ainvoke"):
        result = await llm.ainvoke(messages)
    else:
        result = await asyncio.to_thread(llm.invoke, messages)

    if isinstance(result, schema):
        return result

    if isinstance(result, BaseModel):
        return schema.model_validate(result.model_dump())

    return schema.model_validate(result)


def _download_document(
    bucket_service: MinioBucketService,
    document: OriginalDocumentState,
    output_dir: Path,
    index: int,
) -> Path:
    source = document.get("file_url") or document.get("url") or document.get("key")
    if not source:
        raise ValueError("Original document has no file_url, url, or key")

    suffix = _document_suffix(document)
    destination_path = output_dir / f"document-{index}{suffix}"
    bucket_service.download_file(source, destination_path)
    return destination_path


def _document_suffix(document: OriginalDocumentState) -> str:
    original_name = document.get("original_name")
    if original_name:
        suffix = Path(original_name).suffix
        if suffix:
            return suffix

    mime_type = document.get("mime_type")
    if mime_type == "application/pdf":
        return ".pdf"
    if mime_type == "image/png":
        return ".png"
    if mime_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"

    source = document.get("file_url") or document.get("url") or document.get("key") or ""
    suffix = Path(source).suffix
    return suffix or ".bin"


def _document_to_pil_pages(document_path: Path, mime_type: str | None) -> list[Any]:
    if mime_type == "application/pdf" or document_path.suffix.lower() == ".pdf":
        return _pdf_to_pil_pages(document_path)

    return [_image_file_to_pil_image(document_path)]


def _pdf_to_pil_pages(document_path: Path) -> list[Any]:
    import fitz
    from PIL import Image

    pages: list[Any] = []
    with fitz.open(str(document_path)) as pdf:
        for page in pdf:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pages.append(Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples))

    return pages


def _image_file_to_pil_image(document_path: Path) -> Any:
    from PIL import Image

    with Image.open(document_path) as image:
        return image.convert("RGB").copy()


def _get_visual_boxes_by_page(
    elements: list[Any],
    page_images: list[Any],
) -> dict[int, list[tuple[float, float, float, float]]]:
    boxes_by_page: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)

    for element in elements:

        category = getattr(element, "category", None) or element.__class__.__name__
        if str(category) not in VISUAL_ELEMENT_CATEGORIES:
            continue

        metadata = getattr(element, "metadata", None)
        page_number = int(getattr(metadata, "page_number", 1) or 1)
        local_page_index = page_number - 1

        if local_page_index < 0 or local_page_index >= len(page_images):
            continue

        box = _extract_element_box(element, page_images[local_page_index])
        if box is None:
            continue

        boxes_by_page[local_page_index].append(box)

    return boxes_by_page

def _extract_element_box(element: Any, page_image: Any) -> tuple[float, float, float, float] | None:
    metadata = getattr(element, "metadata", None)
    coordinates = getattr(metadata, "coordinates", None)
    points = getattr(coordinates, "points", None)

    if not points:
        return None

    x_values = [float(point[0]) for point in points]
    y_values = [float(point[1]) for point in points]
    raw_box = (min(x_values), min(y_values), max(x_values), max(y_values))
    source_width, source_height = _get_coordinate_system_size(coordinates)

    if source_width and source_height:
        x_scale = page_image.width / source_width
        y_scale = page_image.height / source_height
        raw_box = (
            raw_box[0] * x_scale,
            raw_box[1] * y_scale,
            raw_box[2] * x_scale,
            raw_box[3] * y_scale,
        )

    return _normalize_box(raw_box, page_image.width, page_image.height)


def _get_coordinate_system_size(coordinates: Any) -> tuple[float | None, float | None]:
    system = getattr(coordinates, "system", None)
    width = _read_attr_or_key(system, "width")
    height = _read_attr_or_key(system, "height")

    if width is None or height is None:
        return None, None

    return float(width), float(height)


def _read_attr_or_key(source: Any, key: str) -> Any:
    if source is None:
        return None

    if isinstance(source, dict):
        return source.get(key)

    return getattr(source, key, None)


def _normalize_box(
    box: tuple[float, float, float, float],
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float] | None:
    x1, y1, x2, y2 = box
    x1 = max(0, min(x1, image_width))
    y1 = max(0, min(y1, image_height))
    x2 = max(0, min(x2, image_width))
    y2 = max(0, min(y2, image_height))

    if x2 - x1 < 8 or y2 - y1 < 8:
        return None

    return x1, y1, x2, y2


def _draw_numbered_box(image: Any, box: tuple[float, float, float, float], box_id: int) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    x1, y1, x2, y2 = box
    line_width = max(4, round(min(image.width, image.height) * 0.006))
    draw.rectangle((x1, y1, x2, y2), outline=(220, 38, 38), width=line_width)

    label = f"[{box_id}]"
    font = _get_label_font(image)
    padding = max(6, line_width)
    text_box = draw.textbbox((0, 0), label, font=font)
    label_width = text_box[2] - text_box[0] + padding * 2
    label_height = text_box[3] - text_box[1] + padding * 2
    label_x = max(0, min(round(x1), image.width - label_width))
    label_y = round(y1) - label_height - line_width

    if label_y < 0:
        label_y = min(image.height - label_height, round(y1) + line_width)

    draw.rectangle(
        (label_x, label_y, label_x + label_width, label_y + label_height),
        fill=(220, 38, 38),
    )
    draw.text((label_x + padding, label_y + padding), label, fill=(255, 255, 255), font=font)


def _get_label_font(image: Any) -> Any:
    from PIL import ImageFont

    font_size = max(22, round(min(image.width, image.height) * 0.035))

    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except OSError:
        return ImageFont.load_default()


def _crop_and_upload_question_image(
    *,
    bucket_service: MinioBucketService,
    state: ExamProcessingState,
    box_ids: list[int],
    exam_order: int,
) -> str | None:
    if not box_ids:
        return None

    page_index, merged_box = _get_merged_box_for_ids(state.get("layout_elements", {}), box_ids)

    if page_index is None or merged_box is None:
        return None

    original_pages_base64 = state.get("original_pages_base64", [])
    if page_index >= len(original_pages_base64):
        return None

    original_page = _base64_to_pil_image(original_pages_base64[page_index])
    crop_box = _expand_box(merged_box, original_page.width, original_page.height)
    cropped_image = original_page.crop(crop_box)
    image_bytes = _pil_image_to_jpeg_bytes(cropped_image)
    uploaded = bucket_service.upload_bytes(
        image_bytes,
        f"question-{exam_order}.jpg",
        folder=f"exams/{state['exam_id']}/question-images",
        content_type="image/jpeg",
    )

    return uploaded.file_url


def _get_merged_box_for_ids(
    layout_elements: dict[int, LayoutElementState],
    box_ids: list[int],
) -> tuple[int | None, tuple[float, float, float, float] | None]:
    boxes_by_page: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)

    for box_id in box_ids:
        element = layout_elements.get(int(box_id))
        if element is None:
            continue

        boxes_by_page[element["page_index"]].append(element["coordinates"])

    if not boxes_by_page:
        return None, None

    page_index = max(boxes_by_page, key=lambda index: len(boxes_by_page[index]))
    boxes = boxes_by_page[page_index]
    merged_box = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )

    return page_index, merged_box


def _expand_box(
    box: tuple[float, float, float, float],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    padding = max(12, round(min(image_width, image_height) * 0.015))

    return (
        max(0, round(x1) - padding),
        max(0, round(y1) - padding),
        min(image_width, round(x2) + padding),
        min(image_height, round(y2) + padding),
    )


def _base64_to_pil_image(image_base64: str) -> Any:
    from PIL import Image

    with Image.open(BytesIO(base64.b64decode(image_base64))) as image:
        return image.convert("RGB").copy()


def _pil_image_to_jpeg_bytes(image: Any) -> bytes:
    with BytesIO() as output:
        image.convert("RGB").save(output, format="JPEG", quality=92)
        return output.getvalue()


def _pil_image_to_jpeg_base64(image: Any) -> str:
    return base64.b64encode(_pil_image_to_jpeg_bytes(image)).decode("ascii")


async def _delete_existing_questions(db: AsyncSession, exam_id: UUID) -> None:
    result = await db.execute(
        select(QuestionModel).options(selectinload(QuestionModel.options)).where(QuestionModel.exam_id == exam_id)
    )

    for question in result.scalars().all():
        await db.delete(question)

    await db.flush()


async def _get_or_create_category(
    db: AsyncSession,
    category_cache: dict[str, CategoryModel],
    category_name: str,
) -> CategoryModel:
    normalized_name = _normalize_category_name(category_name)

    if normalized_name in category_cache:
        return category_cache[normalized_name]

    result = await db.execute(select(CategoryModel).where(CategoryModel.name == normalized_name))
    category = result.scalar_one_or_none()

    if category is None:
        category = CategoryModel(name=normalized_name)
        db.add(category)
        await db.flush()

    category_cache[normalized_name] = category
    return category


def _normalize_category_name(category_name: str) -> str:
    normalized = " ".join(category_name.strip().split())
    return (normalized or "Uncategorized")[:100]


def _sorted_documents(documents: list[OriginalDocumentState]) -> list[OriginalDocumentState]:
    return sorted(documents, key=lambda document: int(document.get("page_order", 0)))


def _build_data_url(base64_data: str, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64_data}"
