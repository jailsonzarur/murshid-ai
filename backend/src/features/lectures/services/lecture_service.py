from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.categories.repository import get_category_by_id
from src.features.files.services.bucket_service import get_bucket_service
from src.features.lectures.ai.final_summary_agent import build_final_summary
from src.features.lectures.ai.live_insight_agent import generate_live_insight
from src.features.lectures.ai.mindmap_tree_agent import build_final_tree
from src.features.lectures.ai.transcription import transcribe_audio_chunk
from src.features.lectures.models import LectureModel, LectureSegmentModel, LectureStatus
from src.features.lectures.repository import (
    add_segment,
    create_lecture,
    delete_lecture,
    get_lecture_by_id,
    get_lecture_with_segments,
    list_lectures_for_user,
)
from src.features.lectures.schemas.lecture_schemas import (
    LectureDetailSchema,
    LectureNodeSchema,
    LectureSegmentSchema,
    LectureSummarySchema,
    ProcessSegmentResponseSchema,
    StartLectureSchema,
)

logger = logging.getLogger(__name__)


def _nodes_from_mindmap(lecture: LectureModel) -> list[dict]:
    data = lecture.mindmap_data
    if not data:
        return []
    nodes = data.get("nodes")
    return nodes if isinstance(nodes, list) else []


def _nodes_count(lecture: LectureModel) -> int:
    return len(_nodes_from_mindmap(lecture))


def _build_summary(lecture: LectureModel) -> LectureSummarySchema:
    return LectureSummarySchema.model_validate(
        {
            "id": lecture.id,
            "user_id": lecture.user_id,
            "category": lecture.category,
            "title": lecture.title,
            "status": lecture.status,
            "duration_seconds": lecture.duration_seconds,
            "nodes_count": _nodes_count(lecture),
            "created_at": lecture.created_at,
            "updated_at": lecture.updated_at,
        }
    )


def _build_detail(lecture: LectureModel) -> LectureDetailSchema:
    return LectureDetailSchema(
        id=lecture.id,
        user_id=lecture.user_id,
        category=lecture.category,  # type: ignore[arg-type]
        title=lecture.title,
        status=lecture.status,
        duration_seconds=lecture.duration_seconds,
        summary=lecture.summary,
        nodes=[LectureNodeSchema.model_validate(node) for node in _nodes_from_mindmap(lecture)],
        segments=[LectureSegmentSchema.model_validate(segment) for segment in lecture.segments],
        created_at=lecture.created_at,
        updated_at=lecture.updated_at,
    )


class ImportAudioItem(TypedDict):
    filename: str
    content: bytes
    content_type: str | None
    duration: float


async def start_lecture(
    db: AsyncSession,
    *,
    user_id: UUID,
    payload: StartLectureSchema,
) -> LectureSummarySchema:
    if payload.category_id is not None:
        category = await get_category_by_id(db, payload.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "errors": ["Matéria não encontrada."], "data": None},
            )

    lecture = LectureModel(
        user_id=user_id,
        title=payload.title,
        category_id=payload.category_id,
    )
    await create_lecture(db, lecture)
    await db.commit()
    await db.refresh(lecture, ["category"])
    return _build_summary(lecture)


async def pause_lecture(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
) -> LectureSummarySchema:
    lecture = await get_lecture_by_id(db, lecture_id)
    if not lecture or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    if lecture.status != LectureStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Somente aulas ativas podem ser pausadas."], "data": None},
        )
    lecture.status = LectureStatus.PAUSED
    await db.commit()
    return _build_summary(lecture)


async def resume_lecture(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
) -> LectureSummarySchema:
    lecture = await get_lecture_by_id(db, lecture_id)
    if not lecture or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    if lecture.status != LectureStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Somente aulas pausadas podem ser retomadas."], "data": None},
        )
    lecture.status = LectureStatus.ACTIVE
    await db.commit()
    return _build_summary(lecture)


async def finish_lecture(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
) -> LectureSummarySchema:
    lecture = await get_lecture_by_id(db, lecture_id)
    if not lecture or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    if lecture.status not in (LectureStatus.ACTIVE, LectureStatus.PAUSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Aula já foi encerrada."], "data": None},
        )
    lecture.status = LectureStatus.COMPLETED
    await db.commit()

    from src.features.lectures.tasks import generate_lecture_summary_task
    cast(Any, generate_lecture_summary_task).delay(str(lecture_id))

    return _build_summary(lecture)


async def get_lecture_detail(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
) -> LectureDetailSchema:
    lecture = await get_lecture_with_segments(db, lecture_id)
    if not lecture or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    return _build_detail(lecture)


async def list_user_lectures(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> list[LectureSummarySchema]:
    lectures = await list_lectures_for_user(db, user_id)
    return [_build_summary(lecture) for lecture in lectures]


async def _transcribe_and_persist_segment(
    db: AsyncSession,
    lecture: LectureModel,
    *,
    audio_bytes: bytes,
    filename: str,
    sequence: int,
    duration: float,
) -> LectureSegmentModel:
    """Transcreve o áudio, cria o segment e atualiza a duração da lecture.

    Não valida ownership/status — o caller faz.
    Não dá commit — o caller agrupa transações.
    """
    transcript = await transcribe_audio_chunk(audio_bytes, filename)
    new_offset = lecture.duration_seconds + duration
    segment = LectureSegmentModel(
        lecture_id=lecture.id,
        sequence=sequence,
        transcript=transcript,
        duration_seconds=duration,
        offset_seconds=new_offset,
    )
    await add_segment(db, segment)
    lecture.duration_seconds = new_offset
    return segment


async def process_segment(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
    audio_bytes: bytes,
    filename: str,
    sequence: int,
    duration: float,
) -> ProcessSegmentResponseSchema:
    lecture = await get_lecture_with_segments(db, lecture_id)
    if not lecture or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    if lecture.status != LectureStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Segmentos só podem ser enviados em aulas ativas."], "data": None},
        )

    segment = await _transcribe_and_persist_segment(
        db,
        lecture,
        audio_bytes=audio_bytes,
        filename=filename,
        sequence=sequence,
        duration=duration,
    )

    # últimos 3 transcripts (anteriores ordenados por sequence) + o novo
    prior = sorted(
        (s for s in lecture.segments if s.id != segment.id),
        key=lambda s: s.sequence,
    )[-2:]
    recent_transcripts = [s.transcript for s in prior] + [segment.transcript]

    insight = await generate_live_insight(recent_transcripts)

    await db.commit()

    return ProcessSegmentResponseSchema(
        segment=LectureSegmentSchema.model_validate(segment),
        insight_message=insight,
    )


async def start_import_lecture(
    db: AsyncSession,
    *,
    user_id: UUID,
    title: str | None,
    category_id: UUID | None,
    audio_items: list[ImportAudioItem],
) -> LectureSummarySchema:
    """Cria uma lecture em PROCESSING, sobe os áudios pro MinIO e dispara a Celery task."""
    if not audio_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Envie pelo menos um arquivo de áudio."], "data": None},
        )

    if category_id is not None:
        category = await get_category_by_id(db, category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "errors": ["Matéria não encontrada."], "data": None},
            )

    lecture = LectureModel(
        user_id=user_id,
        title=title,
        category_id=category_id,
        status=LectureStatus.PROCESSING,
    )
    await create_lecture(db, lecture)
    await db.commit()
    await db.refresh(lecture, ["category"])

    bucket = get_bucket_service()
    task_items: list[dict] = []
    uploaded_keys: list[str] = []
    try:
        for index, item in enumerate(audio_items, start=1):
            folder = f"lectures/{lecture.id}/imports"
            safe_name = f"{index:02d}_{item['filename']}"
            upload = bucket.upload_bytes(
                item["content"],
                safe_name,
                folder=folder,
                content_type=item["content_type"],
            )
            uploaded_keys.append(upload.key)
            task_items.append({"object_key": upload.key, "duration": item["duration"]})
    except Exception:
        logger.exception("start_import_lecture: upload failure for lecture %s", lecture.id)
        for key in uploaded_keys:
            try:
                bucket.delete(key)
            except Exception:
                logger.exception("start_import_lecture: cleanup failed for %s", key)
        lecture.status = LectureStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "errors": ["Falha ao subir os áudios. Tente novamente."], "data": None},
        )

    from src.features.lectures.tasks import process_imported_lecture_task
    cast(Any, process_imported_lecture_task).delay(str(lecture.id), task_items)

    return _build_summary(lecture)


async def remove_lecture(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
) -> None:
    lecture = await get_lecture_by_id(db, lecture_id)
    if not lecture or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    await delete_lecture(db, lecture)
    await db.commit()


async def generate_final_summary(db: AsyncSession, *, lecture_id: UUID) -> None:
    lecture = await get_lecture_with_segments(db, lecture_id)
    if not lecture:
        logger.warning("generate_final_summary: lecture %s not found", lecture_id)
        return

    segments_sorted = sorted(lecture.segments, key=lambda s: s.sequence)
    if not segments_sorted:
        logger.info("generate_final_summary: lecture %s has no segments, skipping", lecture_id)
        return

    full_transcript = "\n\n".join(s.transcript for s in segments_sorted)
    subject_name = lecture.category.name if lecture.category else None

    summary_task = build_final_summary(
        full_transcript=full_transcript,
        lecture_title=lecture.title,
        subject_name=subject_name,
    )
    tree_task = build_final_tree(
        full_transcript=full_transcript,
        lecture_title=lecture.title,
        subject_name=subject_name,
    )

    summary_result, tree_result = await asyncio.gather(summary_task, tree_task)

    if summary_result:
        lecture.summary = summary_result
    if tree_result:
        lecture.mindmap_data = {"nodes": tree_result}

    await db.commit()
    logger.info(
        "generate_final_summary done for %s: summary_len=%d, nodes=%d",
        lecture_id,
        len(summary_result or ""),
        len(tree_result or []),
    )
