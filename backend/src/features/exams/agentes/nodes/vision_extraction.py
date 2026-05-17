from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from decouple import config

from src.features.exams.agentes.nodes.process_layout import format_question_boundary_hints
from src.features.exams.agentes.outputs import invoke_structured_llm
from src.features.exams.agentes.prompts import VISION_EXTRACTION_PROMPT
from src.features.exams.agentes.state import ExamProcessingState
from src.features.exams.schemas.exam_schemas import RawExamExtractionSchema
from src.features.files.services.bucket_service import get_bucket_service

logger = logging.getLogger(__name__)


async def vision_extraction_node(state: ExamProcessingState) -> ExamProcessingState:
    from langchain_core.messages import HumanMessage

    content: list[dict[str, Any]] = [{"type": "text", "text": VISION_EXTRACTION_PROMPT}]
    annotated_pages_base64 = state.get("annotated_pages_base64", [])
    question_boundary_hints = state.get("question_boundary_hints", [])
    if question_boundary_hints:
        content.append({"type": "text", "text": format_question_boundary_hints(question_boundary_hints)})

    for page_index, page_base64 in enumerate(annotated_pages_base64, start=1):
        content.append({"type": "text", "text": f"Annotated page {page_index}"})
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{page_base64}"},
            }
        )

    llm = _get_vision_llm().with_structured_output(RawExamExtractionSchema)
    raw_extracted_data = await invoke_structured_llm(
        llm,
        [HumanMessage(content=cast(Any, content))],
        RawExamExtractionSchema,
    )
    _save_debug_vision_output(raw_extracted_data, state["exam_id"])

    return {**state, "raw_extracted_data": raw_extracted_data}


def _get_vision_llm():
    from langchain_openai import ChatOpenAI

    model_name = str(config("EXAM_VISION_MODEL", default=config("OPENAI_VISION_MODEL", default="gpt-4o")))
    api_key = str(config("OPENAI_API_KEY", default="")).strip()
    kwargs: dict[str, Any] = {"model": model_name, "temperature": 0}

    if api_key:
        kwargs["api_key"] = api_key

    return ChatOpenAI(**kwargs)


def _save_debug_vision_output(raw_extracted_data: RawExamExtractionSchema, exam_id: UUID) -> None:
    if not config("EXAM_VISION_DEBUG_ENABLED", default=True, cast=bool):
        return

    output_content = json.dumps(
        raw_extracted_data.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    try:
        debug_dir = Path(str(config("EXAM_VISION_DEBUG_DIR", default="/tmp/exam-vision-debug")).strip()).expanduser()
        debug_dir = debug_dir / str(exam_id)
        debug_dir.mkdir(parents=True, exist_ok=True)
        output_path = debug_dir / "vision-output.json"
        output_path.write_bytes(output_content)
        logger.info("Saved vision extraction debug output: %s", output_path)
    except OSError:
        logger.exception("Failed to save vision extraction debug output for exam %s", exam_id)

    try:
        uploaded = get_bucket_service().upload_bytes(
            output_content,
            "vision-output.json",
            content_type="application/json",
            key=f"exams/{exam_id}/debug/vision-output.json",
        )
        logger.info("Uploaded vision extraction debug output: %s", uploaded.file_url)
    except Exception:
        logger.exception("Failed to upload vision extraction debug output for exam %s", exam_id)
