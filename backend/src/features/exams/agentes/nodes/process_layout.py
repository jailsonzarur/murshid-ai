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
from typing import Any
from uuid import UUID

from decouple import config

from src.features.exams.agentes.state import (
    ExamProcessingState,
    OriginalDocumentState,
    QuestionStartState,
    VisualBoxState,
)
from src.features.files.services.bucket_service import MinioBucketService, get_bucket_service

logger = logging.getLogger(__name__)

VISUAL_ELEMENT_CATEGORIES = {"Image", "Figure", "Table"}
QUESTION_START_PATTERN = re.compile(
    r"^\s*(?:quest(?:ão|ao)?\s*)?(\d{1,3})(?:\s*[\.\-–:]|\s*$)",
    re.IGNORECASE,
)


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

        sorted_documents = sorted(
            state.get("original_docs", []),
            key=lambda document: int(document.get("page_order", 0)),
        )
        for document_index, document in enumerate(sorted_documents, start=1):
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


def format_question_boundary_hints(question_boundary_hints: list[str]) -> str:
    formatted_hints = "\n".join(f"- {hint}" for hint in question_boundary_hints)
    return (
        "QUESTION BOUNDARY HINTS FROM OCR/LAYOUT PREPROCESSING:\n"
        "Use these hints to associate red box IDs with the correct question. These hints are derived from detected "
        "question-number positions and should override simple visual proximity when a page break occurs.\n"
        f"{formatted_hints}"
    )


def _partition_document(document_path: Path) -> list[Any]:
    from unstructured.partition.auto import partition

    if not shutil.which("tesseract"):
        raise RuntimeError(
            "Tesseract OCR is required by unstructured hi_res layout extraction, but the `tesseract` binary was not "
            "found in PATH. Install it locally with `brew install tesseract` before running the Celery worker on "
            "macOS. If you need Portuguese OCR data, also install `brew install tesseract-lang` and set "
            "EXAM_OCR_LANGUAGES=por,eng."
        )

    raw_languages = str(config("EXAM_OCR_LANGUAGES", default="eng"))
    languages = [language.strip() for language in raw_languages.split(",") if language.strip()]

    return partition(
        filename=str(document_path),
        strategy="hi_res",
        languages=languages or ["eng"],
        pdf_infer_table_structure=True,
    )


def _download_document(
    bucket_service: MinioBucketService,
    document: OriginalDocumentState,
    output_dir: Path,
    index: int,
) -> Path:
    source = document.get("file_url") or document.get("url") or document.get("key")
    if not source:
        raise ValueError("Original document has no file_url, url, or key")

    original_name = document.get("original_name")
    if original_name and Path(original_name).suffix:
        suffix = Path(original_name).suffix
    elif document.get("mime_type") == "application/pdf":
        suffix = ".pdf"
    elif document.get("mime_type") == "image/png":
        suffix = ".png"
    elif document.get("mime_type") in {"image/jpeg", "image/jpg"}:
        suffix = ".jpg"
    else:
        suffix = Path(source).suffix or ".bin"

    destination_path = output_dir / f"document-{index}{suffix}"
    bucket_service.download_file(source, destination_path)
    return destination_path


def _document_to_pil_pages(document_path: Path, mime_type: str | None) -> list[Any]:
    from PIL import Image

    if mime_type == "application/pdf" or document_path.suffix.lower() == ".pdf":
        import fitz

        pages: list[Any] = []
        with fitz.open(str(document_path)) as pdf:
            for page in pdf:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pages.append(Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples))

        return pages

    with Image.open(document_path) as image:
        return [image.convert("RGB").copy()]


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

        if not candidate_boxes:
            continue

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
                f"prefer assigning them to Question {question_start['question_number']} unless the printed text "
                "clearly states otherwise."
            )

        hints.append(hint)

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
        if box is not None:
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
    system = getattr(coordinates, "system", None)

    if isinstance(system, dict):
        source_width = system.get("width")
        source_height = system.get("height")
    else:
        source_width = getattr(system, "width", None)
        source_height = getattr(system, "height", None)

    if source_width and source_height:
        x_scale = page_image.width / float(source_width)
        y_scale = page_image.height / float(source_height)
        raw_box = (
            raw_box[0] * x_scale,
            raw_box[1] * y_scale,
            raw_box[2] * x_scale,
            raw_box[3] * y_scale,
        )

    x1, y1, x2, y2 = raw_box
    x1 = max(0, min(x1, page_image.width))
    y1 = max(0, min(y1, page_image.height))
    x2 = max(0, min(x2, page_image.width))
    y2 = max(0, min(y2, page_image.height))

    if x2 - x1 < 8 or y2 - y1 < 8:
        return None

    return x1, y1, x2, y2


def _draw_numbered_box(image: Any, box: tuple[float, float, float, float], box_id: int) -> None:
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(image)
    x1, y1, x2, y2 = box
    line_width = max(4, round(min(image.width, image.height) * 0.006))
    draw.rectangle((x1, y1, x2, y2), outline=(220, 38, 38), width=line_width)

    label = f"[{box_id}]"
    font_size = max(22, round(min(image.width, image.height) * 0.035))

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

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


def _save_debug_question_boundary_hints(question_boundary_hints: list[str], exam_id: UUID) -> None:
    if not config("EXAM_VISION_DEBUG_ENABLED", default=True, cast=bool):
        return

    try:
        debug_dir = Path(str(config("EXAM_VISION_DEBUG_DIR", default="/tmp/exam-vision-debug")).strip()).expanduser()
        debug_dir = debug_dir / str(exam_id)
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
        raw_path = str(config("EXAM_LAYOUT_DEBUG_DIR", default="tmp/exam-layout-debug")).strip()
        debug_dir = Path(raw_path).expanduser()
        if not debug_dir.is_absolute():
            debug_dir = Path(__file__).resolve().parents[5] / debug_dir

        debug_dir = debug_dir / str(exam_id)
        debug_dir.mkdir(parents=True, exist_ok=True)
        output_path = debug_dir / f"annotated-page-{page_index + 1}.jpg"
        image.convert("RGB").save(output_path, format="JPEG", quality=95)
        logger.info("Saved annotated layout debug image: %s", output_path)
    except OSError:
        logger.exception("Failed to save annotated layout debug image for exam %s page %s", exam_id, page_index + 1)


def _pil_image_to_jpeg_base64(image: Any) -> str:
    with BytesIO() as output:
        image.convert("RGB").save(output, format="JPEG", quality=92)
        return base64.b64encode(output.getvalue()).decode("ascii")
