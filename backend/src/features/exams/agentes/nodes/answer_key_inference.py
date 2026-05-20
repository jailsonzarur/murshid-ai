from __future__ import annotations

import asyncio

from src.features.exams.agentes.state import ExamProcessingState
from src.features.exams.schemas.exam_schemas import ExamExtractionSchema, OptionSchema, QuestionSchema
from src.features.questions.services.question_evaluation_service import EvaluationOption, infer_question_answer_key

MAX_PARALLEL_ANSWER_KEY_INFERENCES = 5


async def answer_key_inference_node(state: ExamProcessingState) -> ExamProcessingState:
    extracted_data = state.get("extracted_data")
    if extracted_data is None:
        raise ValueError("No extracted data available to infer answer keys")

    semaphore = asyncio.Semaphore(MAX_PARALLEL_ANSWER_KEY_INFERENCES)

    async def infer_with_limit(question: QuestionSchema) -> QuestionSchema:
        async with semaphore:
            return await _infer_answer_key_for_question(question)

    questions = await asyncio.gather(*(infer_with_limit(question) for question in extracted_data.questions))
    return {**state, "extracted_data": ExamExtractionSchema(questions=list(questions))}


async def _infer_answer_key_for_question(question: QuestionSchema) -> QuestionSchema:
    options = [
        EvaluationOption(
            key=_option_key(option, index),
            letter=option.letter,
            text=option.text,
            is_correct=None,
        )
        for index, option in enumerate(question.options, start=1)
    ]
    inferred = await infer_question_answer_key(
        question_type=question.type,
        statement=question.statement,
        options=options,
    )

    if question.type in {"OBJECTIVE_SINGLE", "OBJECTIVE_MULTI"}:
        correct_keys = set(inferred.correct_option_keys)
        next_options = [
            option.model_copy(update={"is_correct": _option_key(option, index) in correct_keys})
            for index, option in enumerate(question.options, start=1)
        ]
        return question.model_copy(
            update={
                "options": next_options,
                "explanation": inferred.explanation,
                "expected_answer": None,
            }
        )

    return question.model_copy(
        update={
            "options": [option.model_copy(update={"is_correct": None}) for option in question.options],
            "explanation": inferred.explanation,
            "expected_answer": inferred.expected_answer,
        }
    )


def _option_key(option: OptionSchema, index: int) -> str:
    return option.letter or str(index)
