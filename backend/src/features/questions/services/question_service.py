from __future__ import annotations

from uuid import UUID

from src.database import AsyncSessionLocal
from src.features.categories.models import CategoryModel
from src.features.categories.services.category_service import get_or_create_category
from src.features.exams.schemas.exam_schemas import ExamExtractionSchema
from src.features.questions.models import OptionModel, QuestionModel, QuestionType
from src.features.questions.repository import add_question, delete_questions_by_exam_id


async def replace_exam_questions_from_extraction(
    exam_id: UUID,
    extracted_data: ExamExtractionSchema,
    image_urls_by_exam_order: dict[int, str | None],
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await delete_questions_by_exam_id(db, exam_id)

            category_cache: dict[str, CategoryModel] = {}
            for question in extracted_data.questions:
                category = await get_or_create_category(db, category_cache, question.category_name)
                question_model = QuestionModel(
                    exam_id=exam_id,
                    category_id=category.id,
                    type=QuestionType(question.type),
                    statement=question.statement,
                    image_url=image_urls_by_exam_order.get(question.exam_order),
                    justification=None,
                    explanation=question.explanation,
                    expected_answer=question.expected_answer,
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

                add_question(db, question_model)

            await db.commit()
        except Exception:
            await db.rollback()
            raise
