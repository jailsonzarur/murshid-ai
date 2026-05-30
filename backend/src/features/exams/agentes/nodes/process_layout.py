from __future__ import annotations

import base64
import json
import logging
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID

from decouple import config
from pydantic import BaseModel

from src.features.exams.agentes.state import (
    ExamProcessingState,
    OriginalDocumentState,
    QuestionStartState,
    VisualBoxState,
)
from src.features.files.services.bucket_service import MinioBucketService, get_bucket_service

logger = logging.getLogger(__name__)

# ── Schemas Pydantic ──────────────────────────────────────────────────────────

class _VisualElement(BaseModel):
    label: str
    box_2d: list[int]  # [y1, x1, y2, x2] escala 0–1000


class _QuestionMarker(BaseModel):
    number: int
    y: int  # escala 0–1000, 0=topo


class _PageLayout(BaseModel):
    question_markers: list[_QuestionMarker]
    visual_elements: list[_VisualElement]


class _VerificationItem(BaseModel):
    index: int
    relevant: bool
    reason: str


class _VerificationOutput(BaseModel):
    results: list[_VerificationItem]


# ── Prompts ───────────────────────────────────────────────────────────────────

_DETECTION_PROMPT = """
Analyze this exam page and extract:

1. question_markers — each numbered question that STARTS on this page.
   - number: question number as integer (e.g., 1, 2, 15)
   - y: vertical position as integer 0–1000 (0=top, 1000=bottom)
   - Recognize: "Questão 1", "Q1", "1.", "1)", "01.", "QUESTÃO 01", "1 -", "1 –" etc.
   - Report each question number only ONCE at its first occurrence.
   - Return empty list if no numbered question starts on this page.

2. visual_elements — non-text visual content embedded in exam questions:
   photographs, scientific diagrams, maps, graphs, chemical structures, anatomical figures.
   - label: brief description of what the element shows
   - box_2d: [y1, x1, y2, x2] as integers 0–1000 where (0,0)=top-left, (1000,1000)=bottom-right
   - Be generous with bounding boxes to ensure the complete element is captured.
   - EXCLUDE: question text, answer options, headers, footers, page numbers, blank spaces, logos.

Return empty lists if nothing is found.
""".strip()

_VERIFICATION_PROMPT = """
You are analyzing cropped visual elements extracted from an exam page.

For each numbered element, decide if it is a RELEVANT FIGURE for an exam question:

RELEVANT (relevant=true):
- Scientific diagrams (biology, chemistry, physics, geography, etc.)
- Maps, graphs, charts, data plots
- Photographs illustrating a concept or phenomenon
- Chemical structures, anatomical figures, mathematical illustrations
- Any image a student would need to look at to answer a question

NOT RELEVANT (relevant=false):
- University/institution logos or crests
- Decorative borders, watermarks, page stamps
- Page headers/footers with institutional branding
- Generic icons or clip art unrelated to any question
- Any image clearly not part of an exam question

The exam page is provided as context (first image).
Fill one entry per element in order, using its index number.
""".strip()


# ── Node principal ────────────────────────────────────────────────────────────

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
            logger.info(
                "[layout] exam=%s doc=%d pages=%d mime=%s",
                exam_id, document_index, len(clean_pages), document.get("mime_type"),
            )

            for local_page_index, clean_page in enumerate(clean_pages):
                global_page_index = global_page_offset + local_page_index
                logger.info(
                    "[layout] exam=%s page=%d size=%dx%d — calling Gemini",
                    exam_id, global_page_index + 1, clean_page.width, clean_page.height,
                )

                original_pages_base64.append(_pil_image_to_jpeg_base64(clean_page))

                # ── Etapa 1: detecção ────────────────────────────────────────
                page_layout = await _detect_page_layout(clean_page, exam_id, global_page_index)
                logger.info(
                    "[layout] exam=%s page=%d → question_markers=%s visual_elements=%d",
                    exam_id,
                    global_page_index + 1,
                    [m.number for m in page_layout.question_markers],
                    len(page_layout.visual_elements),
                )

                for marker in page_layout.question_markers:
                    y_pixel = marker.y * clean_page.height / 1000
                    logger.debug(
                        "[layout] exam=%s page=%d question_marker: number=%d y=%d y_px=%.1f",
                        exam_id, global_page_index + 1, marker.number, marker.y, y_pixel,
                    )
                    question_starts.append({
                        "question_number": marker.number,
                        "page_index": global_page_index,
                        "y": y_pixel,
                        "text": f"Question {marker.number}",
                    })

                # ── Etapa 2: denormalização + merge ──────────────────────────
                raw_boxes: list[tuple[str, int, int, int, int]] = []
                for el in page_layout.visual_elements:
                    if len(el.box_2d) != 4:
                        logger.warning(
                            "[layout] exam=%s page=%d invalid box_2d for '%s': %s — skipped",
                            exam_id, global_page_index + 1, el.label, el.box_2d,
                        )
                        continue
                    y1_n, x1_n, y2_n, x2_n = el.box_2d
                    raw_boxes.append((
                        el.label,
                        _denorm(x1_n, clean_page.width),
                        _denorm(y1_n, clean_page.height),
                        _denorm(x2_n, clean_page.width),
                        _denorm(y2_n, clean_page.height),
                    ))

                gap_threshold = max(30, round(min(clean_page.width, clean_page.height) * 0.05))
                merged_boxes = _merge_close_boxes(raw_boxes, gap_threshold)
                if len(merged_boxes) < len(raw_boxes):
                    logger.info(
                        "[layout] exam=%s page=%d merged %d→%d boxes (gap_threshold=%dpx)",
                        exam_id, global_page_index + 1, len(raw_boxes), len(merged_boxes), gap_threshold,
                    )

                # ── Etapa 3: refinamento por conteúdo ────────────────────────
                final_padding = max(6, round(min(clean_page.width, clean_page.height) * 0.005))
                refined: list[tuple[str, tuple[float, float, float, float], Any]] = []
                for label, x1, y1, x2, y2 in merged_boxes:
                    rx1, ry1, rx2, ry2 = _refine_bbox_by_content(clean_page, x1, y1, x2, y2)
                    coords = (float(rx1), float(ry1), float(rx2), float(ry2))
                    crop_img = clean_page.crop((
                        max(0, rx1 - final_padding),
                        max(0, ry1 - final_padding),
                        min(clean_page.width, rx2 + final_padding),
                        min(clean_page.height, ry2 + final_padding),
                    ))
                    refined.append((label, coords, crop_img))

                # ── Etapa 4: verificação de relevância ───────────────────────
                crops_for_verification = [
                    (idx, crop_img)
                    for idx, (_, _, crop_img) in enumerate(refined, start=1)
                ]
                verification = await _verify_elements(
                    clean_page, crops_for_verification, exam_id, global_page_index
                )
                relevant_indices = {v.index for v in verification if v.relevant}

                # ── Etapa 5: monta layout_elements e anota página ────────────
                annotated_page = clean_page.copy()
                for idx, (label, coords, _) in enumerate(refined, start=1):
                    if idx not in relevant_indices:
                        logger.debug(
                            "[layout] exam=%s page=%d element=%d '%s' REJECTED by verification",
                            exam_id, global_page_index + 1, idx, label,
                        )
                        continue

                    box_id = box_id_counter
                    logger.debug(
                        "[layout] exam=%s page=%d element=%d '%s' → box_id=%d coords=(%.0f,%.0f,%.0f,%.0f)",
                        exam_id, global_page_index + 1, idx, label,
                        box_id, coords[0], coords[1], coords[2], coords[3],
                    )
                    _draw_numbered_box(annotated_page, coords, box_id)
                    layout_elements[box_id] = {
                        "page_index": global_page_index,
                        "coordinates": coords,
                    }
                    visual_boxes.append({
                        "box_id": box_id,
                        "page_index": global_page_index,
                        "coordinates": coords,
                    })
                    box_id_counter += 1

                _save_debug_annotated_page(annotated_page, exam_id, global_page_index)
                annotated_pages_base64.append(_pil_image_to_jpeg_base64(annotated_page))

            global_page_offset += len(clean_pages)

    question_starts = _deduplicate_question_starts(question_starts)
    logger.info(
        "[layout] exam=%s finished — total_pages=%d questions_detected=%s visual_boxes=%d",
        exam_id,
        len(original_pages_base64),
        [s["question_number"] for s in question_starts],
        len(visual_boxes),
    )
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
        "QUESTION BOUNDARY HINTS FROM VISION LAYOUT ANALYSIS:\n"
        "Use these hints to associate red box IDs with the correct question. These hints are derived from detected "
        "question-number positions and should override simple visual proximity when a page break occurs.\n"
        f"{formatted_hints}"
    )


# ── Chamadas ao Gemini ────────────────────────────────────────────────────────

def _get_gemini_model() -> Any:
    import google.generativeai as genai

    api_key = str(config("GOOGLE_API_KEY", default="")).strip()
    model_name = str(config("EXAM_LAYOUT_MODEL", default="gemini-2.5-flash")).strip()
    if api_key:
        genai.configure(api_key=api_key)  # pyright: ignore[reportPrivateImportUsage]
    return genai.GenerativeModel(model_name)  # pyright: ignore[reportPrivateImportUsage]


async def _detect_page_layout(page: Any, exam_id: UUID, page_index: int) -> _PageLayout:
    import google.generativeai as genai

    model = _get_gemini_model()
    try:
        response = await model.generate_content_async(
            [page, _DETECTION_PROMPT],
            generation_config=genai.GenerationConfig(  # pyright: ignore[reportPrivateImportUsage]
                response_mime_type="application/json",
                response_schema=_PageLayout,
                temperature=0,
            ),
        )
        result = _PageLayout.model_validate_json(response.text)
        logger.debug("[layout] exam=%s page=%d detection raw: %s", exam_id, page_index + 1, response.text[:300])
        return result
    except Exception:
        logger.exception(
            "[layout] exam=%s page=%d Gemini detection failed, using empty layout",
            exam_id, page_index + 1,
        )
        return _PageLayout(question_markers=[], visual_elements=[])


async def _verify_elements(
    page: Any,
    crops: list[tuple[int, Any]],
    exam_id: UUID,
    page_index: int,
) -> list[_VerificationItem]:
    import google.generativeai as genai

    if not crops:
        return []

    def _approve_all() -> list[_VerificationItem]:
        return [_VerificationItem(index=idx, relevant=True, reason="fallback") for idx, _ in crops]

    content: list[Any] = [page, "Exam page (context)."]
    for idx, crop_img in crops:
        content.append(f"Element {idx}:")
        content.append(crop_img)
    content.append(_VERIFICATION_PROMPT)

    model = _get_gemini_model()
    try:
        response = await model.generate_content_async(
            content,
            generation_config=genai.GenerationConfig(  # pyright: ignore[reportPrivateImportUsage]
                response_mime_type="application/json",
                response_schema=_VerificationOutput,
                temperature=0,
            ),
        )
        result = _VerificationOutput.model_validate_json(response.text)
        logger.debug("[layout] exam=%s page=%d verification raw: %s", exam_id, page_index + 1, response.text[:300])
        return result.results
    except Exception:
        logger.exception(
            "[layout] exam=%s page=%d Gemini verification failed, approving all elements",
            exam_id, page_index + 1,
        )
        return _approve_all()


# ── Processamento de bboxes ───────────────────────────────────────────────────

def _denorm(val: int, total: int) -> int:
    return max(0, min(total, round(val * total / 1000)))


def _merge_close_boxes(
    boxes: list[tuple[str, int, int, int, int]],
    gap_threshold: int,
) -> list[tuple[str, int, int, int, int]]:
    def rect_gap(a: tuple, b: tuple) -> float:
        x_gap = max(0, max(a[1] - b[3], b[1] - a[3]))
        y_gap = max(0, max(a[2] - b[4], b[2] - a[4]))
        return (x_gap ** 2 + y_gap ** 2) ** 0.5

    def merge_two(a: tuple, b: tuple) -> tuple:
        label = a[0] if a[0] == b[0] else f"{a[0]} + {b[0]}"
        return (label, min(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3]), max(a[4], b[4]))

    changed = True
    while changed:
        changed = False
        result: list[tuple] = []
        used: set[int] = set()
        for i in range(len(boxes)):
            if i in used:
                continue
            current = boxes[i]
            for j in range(i + 1, len(boxes)):
                if j in used:
                    continue
                if rect_gap(current, boxes[j]) <= gap_threshold:
                    current = merge_two(current, boxes[j])
                    used.add(j)
                    changed = True
            result.append(current)
            used.add(i)
        boxes = result

    return boxes


def _refine_bbox_by_content(
    image: Any,
    x1: int, y1: int, x2: int, y2: int,
    expansion: float = 0.12,
    bg_threshold: int = 240,
) -> tuple[int, int, int, int]:
    from PIL import ImageOps

    w, h = image.width, image.height
    margin_x = max(20, int((x2 - x1) * expansion))
    margin_y = max(20, int((y2 - y1) * expansion))
    exp_x1 = max(0, x1 - margin_x)
    exp_y1 = max(0, y1 - margin_y)
    exp_x2 = min(w, x2 + margin_x)
    exp_y2 = min(h, y2 + margin_y)

    crop = image.crop((exp_x1, exp_y1, exp_x2, exp_y2)).convert("L")
    binary = crop.point(lambda p: 0 if p < bg_threshold else 255, "L")
    content_bbox = ImageOps.invert(binary).getbbox()

    if content_bbox is None:
        return exp_x1, exp_y1, exp_x2, exp_y2

    cx1, cy1, cx2, cy2 = content_bbox
    return exp_x1 + cx1, exp_y1 + cy1, exp_x1 + cx2, exp_y1 + cy2


# ── Funções auxiliares (inalteradas) ──────────────────────────────────────────

def _deduplicate_question_starts(question_starts: list[QuestionStartState]) -> list[QuestionStartState]:
    sorted_starts = sorted(question_starts, key=lambda item: (item["page_index"], item["y"], item["question_number"]))
    seen_numbers: set[int] = set()
    deduped: list[QuestionStartState] = []
    for start in sorted_starts:
        if start["question_number"] not in seen_numbers:
            seen_numbers.add(start["question_number"])
            deduped.append(start)
    return deduped


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


def _pil_image_to_jpeg_base64(image: Any) -> str:
    with BytesIO() as output:
        image.convert("RGB").save(output, format="JPEG", quality=92)
        return base64.b64encode(output.getvalue()).decode("ascii")


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
