from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, TypedDict, cast
from uuid import UUID

from decouple import config
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pipeline_log import short, stage
from src.database import SessionLocal
from src.features.files.services.bucket_service import get_bucket_service
from src.features.lectures.ai.final_summary_agent import build_final_summary
from src.features.lectures.ai.live_insight_agent import generate_live_insight
from src.features.lectures.ai.mindmap_tree_agent import build_final_tree
from src.features.lectures.ai.transcription import transcribe_audio_file
from src.features.lectures.models import (
    GuidedSummaryStatus,
    LectureAudioModel,
    LectureGuidedCitationModel,
    LectureModel,
    LectureSegmentModel,
    LectureStatus,
    MindmapStatus,
)
from src.features.lectures.repository import (
    add_audios,
    add_guided_citation_sync,
    add_segment,
    claim_lecture_guided_summary,
    claim_lecture_mindmap,
    clear_guided_citations_sync,
    create_lecture,
    delete_lecture,
    get_lecture_by_id,
    get_lecture_by_id_sync,
    get_lecture_with_segments,
    get_lecture_with_segments_sync,
    list_lectures_for_user,
    set_lecture_guided_status_sync,
    set_lecture_mindmap_status_sync,
)
from src.features.lectures.schemas.lecture_schemas import (
    LectureDetailSchema,
    LectureNodeSchema,
    LectureSegmentSchema,
    LectureSummarySchema,
    ProcessSegmentResponseSchema,
    StartLectureSchema,
)
from src.features.subjects.repository import get_subject_by_id

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
            "subject": lecture.subject,
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
        subject=lecture.subject,  # type: ignore[arg-type]
        title=lecture.title,
        status=lecture.status,
        duration_seconds=lecture.duration_seconds,
        summary=lecture.summary,
        mindmap_status=lecture.mindmap_status,
        guided_summary=lecture.guided_summary,
        guided_status=lecture.guided_status,
        nodes=[LectureNodeSchema.model_validate(node) for node in _nodes_from_mindmap(lecture)],
        segments=[LectureSegmentSchema.model_validate(segment) for segment in lecture.segments],
        created_at=lecture.created_at,
        updated_at=lecture.updated_at,
    )


class ImportAudioItem(TypedDict):
    filename: str
    stream: BinaryIO
    size: int
    content_type: str | None
    duration: float


async def start_lecture(
    db: AsyncSession,
    *,
    user_id: UUID,
    payload: StartLectureSchema,
) -> LectureSummarySchema:
    if payload.subject_id is not None:
        subject = await get_subject_by_id(db, payload.subject_id, user_id)
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "errors": ["Matéria não encontrada."], "data": None},
            )

    lecture = LectureModel(
        user_id=user_id,
        title=payload.title,
        subject_id=payload.subject_id,
    )
    await create_lecture(db, lecture)
    await db.commit()
    await db.refresh(lecture, ["subject"])
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
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".webm") as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        transcript = await transcribe_audio_file(Path(tmp.name))
    segment = LectureSegmentModel(
        lecture=lecture,
        sequence=sequence,
        transcript=transcript,
        duration_seconds=duration,
        offset_seconds=lecture.duration_seconds,
    )
    await add_segment(db, segment)
    lecture.duration_seconds += duration
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
    subject_id: UUID | None,
    audio_items: list[ImportAudioItem],
) -> LectureSummarySchema:
    """Cria uma lecture em PROCESSING, sobe os áudios pro MinIO e dispara a Celery task."""
    if not audio_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "errors": ["Envie pelo menos um arquivo de áudio."], "data": None},
        )

    if subject_id is not None:
        subject = await get_subject_by_id(db, subject_id, user_id)
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "errors": ["Matéria não encontrada."], "data": None},
            )

    lecture = LectureModel(
        user_id=user_id,
        title=title,
        subject_id=subject_id,
        status=LectureStatus.PROCESSING,
    )
    await create_lecture(db, lecture)
    await db.commit()
    await db.refresh(lecture, ["subject"])

    bucket = get_bucket_service()
    audios: list[LectureAudioModel] = []
    uploaded_keys: list[str] = []
    try:
        for index, item in enumerate(audio_items, start=1):
            folder = f"lectures/{lecture.id}/imports"
            safe_name = f"{index:02d}_{item['filename']}"
            upload = await asyncio.to_thread(
                bucket.upload_stream,
                item["stream"],
                safe_name,
                length=item["size"],
                folder=folder,
                content_type=item["content_type"],
            )
            uploaded_keys.append(upload.key)
            audios.append(
                LectureAudioModel(
                    lecture_id=lecture.id,
                    sequence=index,
                    object_key=upload.key,
                    original_filename=item["filename"],
                    duration_seconds=float(item["duration"]),
                )
            )
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

    await add_audios(db, audios)
    await db.commit()

    from src.features.lectures.tasks import dispatch_import_lecture
    dispatch_import_lecture(lecture.id)

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


def generate_final_summary(lecture_id: UUID) -> None:
    with stage("generate_summary", lecture=short(lecture_id)):
        _generate_final_summary(lecture_id)


def _generate_final_summary(lecture_id: UUID) -> None:
    with SessionLocal() as db:
        lecture = get_lecture_with_segments_sync(db, lecture_id)
        if not lecture:
            logger.warning("generate_final_summary: lecture %s not found", lecture_id)
            return
        if lecture.summary is not None:
            logger.info("generate_final_summary: lecture %s already summarised", lecture_id)
            return

        segments_sorted = sorted(lecture.segments, key=lambda s: s.sequence)
        if not segments_sorted:
            logger.info("generate_final_summary: lecture %s has no segments, skipping", lecture_id)
            return

        full_transcript = "\n\n".join(s.transcript for s in segments_sorted)
        lecture_title = lecture.title
        subject_name = lecture.subject.name if lecture.subject else None

    summary_result = build_final_summary(
        full_transcript=full_transcript,
        lecture_title=lecture_title,
        subject_name=subject_name,
    )

    with SessionLocal() as db:
        lecture = get_lecture_by_id_sync(db, lecture_id)
        if lecture is None:
            logger.warning("generate_final_summary: lecture %s vanished mid-generation", lecture_id)
            return
        if summary_result:
            lecture.summary = summary_result
        db.commit()

    logger.info(
        "generate_final_summary done for %s: summary_len=%d",
        lecture_id,
        len(summary_result or ""),
    )


def generate_mindmap(lecture_id: UUID) -> None:
    with stage("generate_mindmap", lecture=short(lecture_id)):
        try:
            _generate_mindmap(lecture_id)
        except Exception:
            _set_mindmap_status(lecture_id, MindmapStatus.FAILED)
            raise


def _set_mindmap_status(lecture_id: UUID, value: MindmapStatus) -> None:
    with SessionLocal() as db:
        set_lecture_mindmap_status_sync(db, lecture_id, value)
        db.commit()


def _generate_mindmap(lecture_id: UUID) -> None:
    with SessionLocal() as db:
        lecture = get_lecture_by_id_sync(db, lecture_id)
        if lecture is None:
            logger.warning("generate_mindmap: lecture %s not found", lecture_id)
            return
        if lecture.mindmap_data is not None:
            logger.info("generate_mindmap: lecture %s already has a mindmap", lecture_id)
            lecture.mindmap_status = MindmapStatus.DONE
            db.commit()
            return
        if not lecture.summary:
            logger.info("generate_mindmap: lecture %s has no summary yet", lecture_id)
            _set_mindmap_status(lecture_id, MindmapStatus.FAILED)
            return

        summary = lecture.summary
        lecture_title = lecture.title
        subject_name = lecture.subject.name if lecture.subject else None

    tree_result = build_final_tree(
        summary=summary,
        lecture_title=lecture_title,
        subject_name=subject_name,
    )
    if not tree_result:
        logger.warning("generate_mindmap: empty tree for lecture %s", lecture_id)
        _set_mindmap_status(lecture_id, MindmapStatus.FAILED)
        return

    with SessionLocal() as db:
        lecture = get_lecture_by_id_sync(db, lecture_id)
        if lecture is None or lecture.mindmap_data is not None:
            return
        lecture.mindmap_data = {"nodes": tree_result}
        lecture.mindmap_status = MindmapStatus.DONE
        db.commit()

    logger.info("generate_mindmap done for %s: nodes=%d", lecture_id, len(tree_result))


GUIDED_MAX_DISTANCE = float(str(config("GUIDED_MAX_DISTANCE", default="0.45")).strip())
GUIDED_MAX_EXCERPTS = int(str(config("GUIDED_MAX_EXCERPTS", default="3")).strip())


async def request_guided_summary(db: AsyncSession, lecture_id: UUID, user_id: UUID) -> None:
    lecture = await get_lecture_by_id(db, lecture_id)
    if lecture is None or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    if lecture.guided_summary is not None:
        return
    if not lecture.summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "errors": ["O resumo da aula ainda não está pronto."],
                "data": None,
            },
        )
    if lecture.subject_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "errors": ["A aula precisa de uma matéria com bibliografia anexada."],
                "data": None,
            },
        )

    claimed = await claim_lecture_guided_summary(db, lecture_id)
    await db.commit()
    if not claimed:
        return

    from src.features.lectures.tasks import generate_lecture_guided_summary_task

    cast(Any, generate_lecture_guided_summary_task).delay(str(lecture_id))


def generate_guided_summary(lecture_id: UUID) -> None:
    with stage("generate_guided_summary", lecture=short(lecture_id)):
        try:
            _generate_guided_summary(lecture_id)
        except Exception:
            _set_guided_status(lecture_id, GuidedSummaryStatus.FAILED)
            raise


def _generate_guided_summary(lecture_id: UUID) -> None:
    from src.features.lectures.ai.guided_summary_agent import (
        Excerpt,
        TopicContext,
        build_guided_summary,
    )
    from src.features.lectures.ai.guided_topics_agent import extract_topics
    from src.features.subjects.ai.embedding import embed_texts
    from src.features.subjects.repository import search_subject_chunks_sync

    with SessionLocal() as db:
        lecture = get_lecture_with_segments_sync(db, lecture_id)
        if lecture is None:
            logger.warning("generate_guided_summary: lecture %s not found", lecture_id)
            return
        if lecture.guided_summary is not None:
            logger.info("generate_guided_summary: lecture %s already guided", lecture_id)
            lecture.guided_status = GuidedSummaryStatus.DONE
            db.commit()
            return
        if not lecture.summary or lecture.subject_id is None:
            logger.info("generate_guided_summary: lecture %s is not ready", lecture_id)
            set_lecture_guided_status_sync(db, lecture_id, GuidedSummaryStatus.FAILED)
            db.commit()
            return

        lecture.guided_status = GuidedSummaryStatus.PROCESSING
        db.commit()

        summary = lecture.summary
        subject_id = lecture.subject_id
        lecture_title = lecture.title
        subject_name = lecture.subject.name if lecture.subject else None
        transcript = "\n".join(segment.transcript for segment in lecture.segments)

    topics = extract_topics(summary, transcript)
    if not topics:
        logger.warning("generate_guided_summary: no topics for %s", lecture_id)
        _set_guided_status(lecture_id, GuidedSummaryStatus.FAILED)
        return

    vectors = embed_texts([topic["query"] for topic in topics])

    contexts: list[TopicContext] = []
    audits: list[tuple[str, str, list[dict]]] = []
    number = 0

    with SessionLocal() as db:
        documents = _document_titles(db, subject_id)
        for topic, vector in zip(topics, vectors, strict=True):
            found = search_subject_chunks_sync(
                db, subject_id, vector, limit=GUIDED_MAX_EXCERPTS
            )
            excerpts: list[Excerpt] = []
            results: list[dict] = []

            for chunk, distance in found:
                used = distance <= GUIDED_MAX_DISTANCE
                if used:
                    number += 1
                    excerpts.append(
                        Excerpt(
                            number=number,
                            document=documents.get(chunk.document_id, "?"),
                            heading_path=chunk.heading_path,
                            page=chunk.page_start,
                            text=chunk.text,
                        )
                    )
                results.append(
                    {
                        "n": number if used else None,
                        "chunk_id": str(chunk.id),
                        "distance": round(distance, 4),
                        "heading_path": chunk.heading_path,
                        "page_start": chunk.page_start,
                        "text": chunk.text,
                        "used": used,
                    }
                )

            contexts.append(
                TopicContext(
                    title=topic["title"], summary_section=topic["query"], excerpts=excerpts
                )
            )
            audits.append((topic["title"], topic["query"], results))

    guided = build_guided_summary(transcript, contexts, lecture_title, subject_name)
    if not guided.strip():
        logger.warning("generate_guided_summary: empty output for %s", lecture_id)
        _set_guided_status(lecture_id, GuidedSummaryStatus.FAILED)
        return

    with SessionLocal() as db:
        clear_guided_citations_sync(db, lecture_id)
        for topic_title, query, results in audits:
            add_guided_citation_sync(
                db,
                LectureGuidedCitationModel(
                    lecture_id=lecture_id, topic=topic_title, query=query, results=results
                ),
            )

        lecture = get_lecture_by_id_sync(db, lecture_id)
        if lecture is not None:
            lecture.guided_summary = guided
            lecture.guided_status = GuidedSummaryStatus.DONE
        db.commit()

    logger.info(
        "generate_guided_summary done for %s: topics=%d excerpts=%d chars=%d",
        lecture_id,
        len(contexts),
        number,
        len(guided),
    )


def _document_titles(db, subject_id: UUID) -> dict[UUID, str]:
    from sqlalchemy import select

    from src.features.subjects.models import SubjectDocumentModel

    rows = db.execute(
        select(SubjectDocumentModel.id, SubjectDocumentModel.title).where(
            SubjectDocumentModel.subject_id == subject_id
        )
    ).all()
    return {row.id: row.title for row in rows}


def _set_guided_status(lecture_id: UUID, value: GuidedSummaryStatus) -> None:
    with SessionLocal() as db:
        set_lecture_guided_status_sync(db, lecture_id, value)
        db.commit()


async def change_lecture_subject(
    db: AsyncSession, lecture_id: UUID, user_id: UUID, subject_id: UUID | None
) -> LectureDetailSchema:
    from src.features.subjects.repository import get_subject_by_id

    lecture = await get_lecture_with_segments(db, lecture_id)
    if lecture is None or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )

    if subject_id is not None and await get_subject_by_id(db, subject_id, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Matéria não encontrada."], "data": None},
        )

    lecture.subject_id = subject_id
    await db.commit()
    await db.refresh(lecture, attribute_names=["subject"])

    return _build_detail(lecture)


async def request_mindmap(db: AsyncSession, lecture_id: UUID, user_id: UUID) -> None:
    lecture = await get_lecture_by_id(db, lecture_id)
    if lecture is None or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    if lecture.mindmap_data is not None:
        return
    if not lecture.summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "errors": ["O resumo da aula ainda não está pronto."],
                "data": None,
            },
        )

    claimed = await claim_lecture_mindmap(db, lecture_id)
    await db.commit()
    if not claimed:
        return

    from src.features.lectures.tasks import generate_lecture_mindmap_task

    cast(Any, generate_lecture_mindmap_task).delay(str(lecture_id))
