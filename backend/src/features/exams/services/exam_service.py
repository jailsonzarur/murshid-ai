from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import AsyncSessionLocal
from src.features.exams.agentes.state import OriginalDocumentState
from src.features.exams.models import ExamDocumentModel, ExamModel, ExamStatus
from src.features.exams.schemas.exam_schemas import ExamListSchema, ExamViewerOptionSchema, ExamViewerQuestionSchema
from src.features.files.services.bucket_service import get_bucket_service
from src.features.questions.models import QuestionModel

ALLOWED_EXAM_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}


async def list_exams(db: AsyncSession) -> list[ExamListSchema]:
    exams = await get_all_exam_models(db)

    return [
        ExamListSchema(
            id=exam.id,
            name=exam.name,
            general_subject=exam.general_subject,
            status=exam.status,
            documents_count=len(exam.documents),
            created_at=exam.created_at,
            updated_at=exam.updated_at,
        )
        for exam in exams
    ]


async def list_exam_questions(db: AsyncSession, exam_id: UUID) -> list[ExamViewerQuestionSchema]:
    exam = await get_exam_model_with_questions(db, exam_id)

    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Prova nao encontrada"], "data": None},
        )

    bucket_service = get_bucket_service()

    return [
        ExamViewerQuestionSchema(
            id=question.id,
            type=question.type.value,
            statement=question.statement,
            image_url=_get_viewer_image_url(bucket_service, question.image_url),
            options=[
                ExamViewerOptionSchema(id=option.id, text=option.text, letter=option.letter)
                for option in sorted(question.options, key=lambda item: item.letter or "")
            ],
        )
        for question in sorted(exam.questions, key=lambda item: item.exam_order)
    ]


def _get_viewer_image_url(bucket_service, image_url: str | None) -> str | None:
    if not image_url:
        return None

    if image_url.startswith("data:"):
        return image_url

    return bucket_service.get_presigned_url(image_url)


async def create_exam_and_dispatch_task(
    db: AsyncSession,
    name: str,
    general_subject: str | None,
    files: Sequence[UploadFile],
) -> ExamModel:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Envie pelo menos um arquivo"], "data": None},
        )

    bucket_service = get_bucket_service()
    uploaded_file_urls: list[str] = []

    try:
        exam = await create_exam_model(db, ExamModel(name=name, general_subject=general_subject))

        for index, file in enumerate(files, start=1):
            mime_type = file.content_type

            if mime_type not in ALLOWED_EXAM_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "errors": [f"Tipo de arquivo invalido: {mime_type or 'desconhecido'}"],
                        "data": None,
                    },
                )

            content = await file.read()
            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"success": False, "errors": [f"Arquivo vazio: {file.filename}"], "data": None},
                )

            uploaded = bucket_service.upload(
                content,
                file.filename or f"exam-file-{index}",
                folder=f"exams/{exam.id}",
                content_type=mime_type,
            )
            uploaded_file_urls.append(uploaded.file_url)

            add_exam_document_model(
                db,
                ExamDocumentModel(
                    exam_id=exam.id,
                    file_url=uploaded.file_url,
                    original_name=file.filename or uploaded.key,
                    mime_type=mime_type,
                    page_order=index,
                ),
            )

        for file_url in uploaded_file_urls:
            if not bucket_service.verify_exists(file_url):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "success": False,
                        "errors": [f"Falha ao verificar upload no bucket: {file_url}"],
                        "data": None,
                    },
                )

        await commit_exam_transaction(db)
        await refresh_exam_model(db, exam)

        from src.features.exams.tasks import process_exam_task

        cast(Any, process_exam_task).delay(str(exam.id))
        return exam
    except Exception:
        await rollback_exam_transaction(db)
        raise


async def delete_exam(db: AsyncSession, exam_id: UUID) -> None:
    exam = await get_exam_model_for_delete(db, exam_id)

    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Prova nao encontrada"], "data": None},
        )

    bucket_urls = _get_exam_bucket_urls(exam)
    bucket_service = get_bucket_service()

    try:
        bucket_service.delete_many(bucket_urls)
        await delete_exam_model(db, exam)
        await commit_exam_transaction(db)
    except Exception:
        await rollback_exam_transaction(db)
        raise


def _get_exam_bucket_urls(exam: ExamModel) -> list[str]:
    urls = {document.file_url for document in exam.documents}

    for question in exam.questions:
        if question.image_url:
            urls.add(question.image_url)

    return list(urls)


async def mark_exam_as_processing_and_get_documents(exam_id: UUID) -> list[OriginalDocumentState]:
    async with AsyncSessionLocal() as db:
        exam = await get_exam_model_with_documents(db, exam_id)

        if exam is None:
            raise ValueError(f"Exam not found: {exam_id}")

        exam.status = ExamStatus.PROCESSING
        exam.error_log = None
        await db.commit()

        return [
            {
                "file_url": document.file_url,
                "mime_type": document.mime_type,
                "original_name": document.original_name,
                "page_order": document.page_order,
            }
            for document in sorted(exam.documents, key=lambda item: item.page_order)
        ]


async def set_exam_status(exam_id: UUID, status: ExamStatus, *, error_log: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        exam = await db.get(ExamModel, exam_id)

        if exam is None:
            return

        exam.status = status
        exam.error_log = error_log
        await db.commit()


async def get_all_exam_models(db: AsyncSession) -> list[ExamModel]:
    result = await db.execute(
        select(ExamModel).options(selectinload(ExamModel.documents)).order_by(ExamModel.created_at.desc())
    )
    return list(result.scalars().all())


async def get_exam_model_with_documents(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel).options(selectinload(ExamModel.documents)).where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def get_exam_model_for_delete(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .options(
            selectinload(ExamModel.documents),
            selectinload(ExamModel.questions).selectinload(QuestionModel.options),
        )
        .where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def get_exam_model_with_questions(db: AsyncSession, exam_id: UUID) -> ExamModel | None:
    result = await db.execute(
        select(ExamModel)
        .options(selectinload(ExamModel.questions).selectinload(QuestionModel.options))
        .where(ExamModel.id == exam_id)
    )
    return result.scalar_one_or_none()


async def create_exam_model(db: AsyncSession, exam: ExamModel) -> ExamModel:
    db.add(exam)
    await db.flush()
    return exam


def add_exam_document_model(db: AsyncSession, document: ExamDocumentModel) -> None:
    db.add(document)


async def delete_exam_model(db: AsyncSession, exam: ExamModel) -> None:
    await db.delete(exam)


async def commit_exam_transaction(db: AsyncSession) -> None:
    await db.commit()


async def rollback_exam_transaction(db: AsyncSession) -> None:
    await db.rollback()


async def refresh_exam_model(db: AsyncSession, exam: ExamModel) -> None:
    await db.refresh(exam)
