from __future__ import annotations

import json
from typing import Any

from decouple import config

from src.features.exams.agentes.outputs import invoke_structured_llm
from src.features.exams.agentes.prompts import TEXT_STRUCTURING_PROMPT
from src.features.exams.agentes.state import ExamProcessingState
from src.features.exams.schemas.exam_schemas import QuestionSchema, RawQuestionSchema


async def text_structuring_node(state: ExamProcessingState) -> ExamProcessingState:
    raw_extracted_data = state.get("raw_extracted_data")
    if raw_extracted_data is None:
        raise ValueError("No raw extracted data available to structure")

    llm = _get_text_structuring_llm().with_structured_output(QuestionSchema)
    questions: list[QuestionSchema] = []

    for raw_question in raw_extracted_data.questions:
        questions.append(await _structure_raw_question(llm, raw_question))

    from src.features.exams.schemas.exam_schemas import ExamExtractionSchema

    return {**state, "extracted_data": ExamExtractionSchema(questions=questions)}


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
    parsed_question = await invoke_structured_llm(
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


def _get_text_structuring_llm():
    from langchain_openai import ChatOpenAI

    model_name = str(config("EXAM_TEXT_MODEL", default=config("OPENAI_TEXT_MODEL", default="gpt-4o")))
    api_key = str(config("OPENAI_API_KEY", default="")).strip()
    kwargs: dict[str, Any] = {"model": model_name, "temperature": 0}

    if api_key:
        kwargs["api_key"] = api_key

    return ChatOpenAI(**kwargs)
