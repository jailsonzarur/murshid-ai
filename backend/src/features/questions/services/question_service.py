from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import AsyncSessionLocal
from src.features.categories.models import CategoryModel
from src.features.categories.services.category_service import get_or_create_category
from src.features.exams.schemas.exam_schemas import ExamExtractionSchema
from src.features.questions.models import OptionModel, QuestionModel, QuestionType


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


async def delete_questions_by_exam_id(db: AsyncSession, exam_id: UUID) -> None:
    result = await db.execute(
        select(QuestionModel).options(selectinload(QuestionModel.options)).where(QuestionModel.exam_id == exam_id)
    )

    for question in result.scalars().all():
        await db.delete(question)

    await db.flush()
