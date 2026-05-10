from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.exams.models import ExamDocumentModel, ExamModel
from src.features.exams.repository import (
    add_exam_document_record,
    commit_exam_transaction,
    create_exam_record,
    delete_exam_record,
    get_all_exams,
    get_exam_for_delete,
    get_exam_with_questions,
    refresh_exam_record,
    rollback_exam_transaction,
)
from src.features.exams.schemas.exam_schemas import ExamListSchema, ExamViewerOptionSchema, ExamViewerQuestionSchema
from src.features.exams.tasks import process_exam_task
from src.features.files.services.bucket_service import get_bucket_service

ALLOWED_EXAM_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}


async def list_exams(db: AsyncSession) -> list[ExamListSchema]:
    exams = await get_all_exams(db)

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
    exam = await get_exam_with_questions(db, exam_id)

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
        exam = await create_exam_record(db, ExamModel(name=name, general_subject=general_subject))

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

            add_exam_document_record(
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
        await refresh_exam_record(db, exam)
        cast(Any, process_exam_task).delay(str(exam.id))
        return exam
    except Exception:
        await rollback_exam_transaction(db)
        raise


async def delete_exam(db: AsyncSession, exam_id: UUID) -> None:
    exam = await get_exam_for_delete(db, exam_id)

    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Prova nao encontrada"], "data": None},
        )

    bucket_urls = _get_exam_bucket_urls(exam)
    bucket_service = get_bucket_service()

    try:
        bucket_service.delete_many(bucket_urls)
        await delete_exam_record(db, exam)
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
