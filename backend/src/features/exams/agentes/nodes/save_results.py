from __future__ import annotations

import base64
from collections import defaultdict
from io import BytesIO

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

    x1, y1, x2, y2 = merged_box
    padding = max(12, round(min(original_page.width, original_page.height) * 0.015))
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
