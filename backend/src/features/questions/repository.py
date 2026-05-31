from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.questions.models import QuestionModel


async def get_questions_with_options_by_exam_id(db: AsyncSession, exam_id: UUID) -> list[QuestionModel]:
    result = await db.execute(
        select(QuestionModel).options(selectinload(QuestionModel.options)).where(QuestionModel.exam_id == exam_id)
    )
    return list(result.scalars().all())


async def delete_questions_by_exam_id(db: AsyncSession, exam_id: UUID) -> None:
    questions = await get_questions_with_options_by_exam_id(db, exam_id)
    for question in questions:
        await db.delete(question)
    await db.flush()


def add_question(db: AsyncSession, question: QuestionModel) -> None:
    db.add(question)
