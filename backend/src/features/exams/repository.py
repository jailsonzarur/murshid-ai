from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.exams.models import ExamDocumentModel, ExamModel
from src.features.questions.models import QuestionModel


async def get_all_exams(db: AsyncSession) -> list[ExamModel]:
    result = await db.execute(
        select(ExamModel).options(selectinload(ExamModel.documents)).order_by(ExamModel.created_at.desc())
    )
    return list(result.scalars().all())


async def get_exam_with_documents(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .options(selectinload(ExamModel.documents))
        .where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def get_exam_for_delete(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .options(
            selectinload(ExamModel.documents),
            selectinload(ExamModel.questions).selectinload(QuestionModel.options),
        )
        .where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def get_exam_with_questions(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .options(selectinload(ExamModel.questions).selectinload(QuestionModel.options))
        .where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def create_exam_record(db: AsyncSession, exam: ExamModel) -> ExamModel:
    db.add(exam)
    await db.flush()
    return exam


def add_exam_document_record(db: AsyncSession, document: ExamDocumentModel) -> None:
    db.add(document)


async def delete_exam_record(db: AsyncSession, exam: ExamModel) -> None:
    await db.delete(exam)


async def commit_exam_transaction(db: AsyncSession) -> None:
    await db.commit()


async def rollback_exam_transaction(db: AsyncSession) -> None:
    await db.rollback()


async def refresh_exam_record(db: AsyncSession, exam: ExamModel) -> None:
    await db.refresh(exam)
