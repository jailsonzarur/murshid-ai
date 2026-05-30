from __future__ import annotations

import base64
from collections import defaultdict
from io import BytesIO
from typing import Any

from src.features.exams.agentes.state import ExamProcessingState, LayoutElementState
from src.features.files.services.bucket_service import MinioBucketService, get_bucket_service
from src.features.questions.services.question_service import replace_exam_questions_from_extraction


async def save_results_node(state: ExamProcessingState) -> ExamProcessingState:
    extracted_data = state.get("extracted_data")
    if extracted_data is None:
        raise ValueError("No extracted data available to save")

    bucket_service = get_bucket_service()
    image_urls_by_exam_order = {
        question.exam_order: _crop_and_upload_question_image(
            bucket_service=bucket_service,
            state=state,
            box_ids=question.box_ids,
            exam_order=question.exam_order,
        )
        for question in extracted_data.questions
    }
    await replace_exam_questions_from_extraction(state["exam_id"], extracted_data, image_urls_by_exam_order)

    return state


def _crop_and_upload_question_image(
    *,
    bucket_service: MinioBucketService,
    state: ExamProcessingState,
    box_ids: list[int],
    exam_order: int,
) -> str | None:
    from PIL import Image

    if not box_ids:
        return None

    page_index, merged_box = _get_merged_box_for_ids(state.get("layout_elements", {}), box_ids)
    if page_index is None or merged_box is None:
        return None

    original_pages_base64 = state.get("original_pages_base64", [])
    if page_index >= len(original_pages_base64):
        return None

    with Image.open(BytesIO(base64.b64decode(original_pages_base64[page_index]))) as image:
        original_page = image.convert("RGB").copy()

    refined_box = _refine_bbox_by_content(original_page, merged_box)
    x1, y1, x2, y2 = refined_box
    padding = max(8, round(min(original_page.width, original_page.height) * 0.008))
    cropped_image = original_page.crop(
        (
            max(0, round(x1) - padding),
            max(0, round(y1) - padding),
            min(original_page.width, round(x2) + padding),
            min(original_page.height, round(y2) + padding),
        )
    )

    with BytesIO() as output:
        cropped_image.convert("RGB").save(output, format="JPEG", quality=92)
        image_bytes = output.getvalue()

    uploaded = bucket_service.upload_bytes(
        image_bytes,
        f"question-{exam_order}.jpg",
        folder=f"exams/{state['exam_id']}/question-images",
        content_type="image/jpeg",
    )

    return uploaded.file_url


def _refine_bbox_by_content(
    image: Any,
    rough_bbox: tuple[float, float, float, float],
    *,
    expansion: float = 0.12,
    bg_threshold: int = 240,
) -> tuple[float, float, float, float]:
    """Expand the rough GPT-4o bbox and trim to actual content pixel boundaries."""
    from PIL import ImageOps

    w, h = image.width, image.height
    x1, y1, x2, y2 = rough_bbox

    margin_x = max(20.0, (x2 - x1) * expansion)
    margin_y = max(20.0, (y2 - y1) * expansion)
    exp_x1 = max(0, int(x1 - margin_x))
    exp_y1 = max(0, int(y1 - margin_y))
    exp_x2 = min(w, int(x2 + margin_x))
    exp_y2 = min(h, int(y2 + margin_y))

    # Binarize: dark content → black (0), light background → white (255)
    expanded_crop = image.crop((exp_x1, exp_y1, exp_x2, exp_y2)).convert("L")
    binary = expanded_crop.point(lambda p: 0 if p < bg_threshold else 255, "L")

    # getbbox() finds bbox of non-black region; invert so content is white
    content_bbox = ImageOps.invert(binary).getbbox()

    if content_bbox is None:
        return (float(exp_x1), float(exp_y1), float(exp_x2), float(exp_y2))

    cx1, cy1, cx2, cy2 = content_bbox
    return (
        float(exp_x1 + cx1),
        float(exp_y1 + cy1),
        float(exp_x1 + cx2),
        float(exp_y1 + cy2),
    )


def _get_merged_box_for_ids(
    layout_elements: dict[int, LayoutElementState],
    box_ids: list[int],
) -> tuple[int | None, tuple[float, float, float, float] | None]:
    boxes_by_page: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)

    for box_id in box_ids:
        element = layout_elements.get(int(box_id))
        if element is not None:
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
