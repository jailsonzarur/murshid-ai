from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.lectures.models import (
    LectureEventModel,
    LectureEventSeverity,
    LectureEventType,
    LectureModel,
    LectureSegmentModel,
    LectureStatus,
)
from src.features.lectures.repository import (
    add_event,
    add_segment,
    create_lecture,
    get_lecture_by_id,
    get_lecture_with_events,
    get_lecture_with_relations,
    list_lectures_for_user,
)
from src.features.lectures.ai.mindmap_agent import generate_final_mindmap_and_summary, update_mindmap
from src.features.lectures.ai.topic_alert_agent import extract_topic_and_alert
from src.features.lectures.ai.transcription import transcribe_audio_chunk
from src.features.lectures.schemas.lecture_schemas import (
    LectureDetailSchema,
    LectureSegmentSchema,
    LectureSummarySchema,
    ProcessSegmentResponseSchema,
    StartLectureSchema,
)


async def start_lecture(
    db: AsyncSession,
    *,
    user_id: UUID,
    payload: StartLectureSchema,
) -> LectureSummarySchema:
    lecture = LectureModel(user_id=user_id, title=payload.title)
    await create_lecture(db, lecture)
    await db.commit()
    return LectureSummarySchema.model_validate(lecture)


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
    return LectureSummarySchema.model_validate(lecture)


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
    return LectureSummarySchema.model_validate(lecture)


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
    generate_lecture_summary_task.delay(str(lecture_id))

    return LectureSummarySchema.model_validate(lecture)


async def get_lecture_detail(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
) -> LectureDetailSchema:
    lecture = await get_lecture_with_relations(db, lecture_id)
    if not lecture or lecture.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "errors": ["Aula não encontrada."], "data": None},
        )
    return LectureDetailSchema.model_validate(lecture)


async def list_user_lectures(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> list[LectureSummarySchema]:
    lectures = await list_lectures_for_user(db, user_id)
    return [LectureSummarySchema.model_validate(lecture) for lecture in lectures]


async def process_segment(
    db: AsyncSession,
    *,
    lecture_id: UUID,
    user_id: UUID,
    audio_bytes: bytes,
    filename: str,
    sequence: int,
    duration: float | None = None,
) -> ProcessSegmentResponseSchema:
    transcript = await transcribe_audio_chunk(audio_bytes, filename)

    lecture = await get_lecture_with_events(db, lecture_id)
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

    existing_topics = [e.content for e in lecture.events if e.type == LectureEventType.TOPIC]
    existing_alerts = [e.content for e in lecture.events if e.type == LectureEventType.ALERT]
    extraction = await extract_topic_and_alert(transcript, existing_topics, existing_alerts)

    segment = LectureSegmentModel(
        lecture_id=lecture_id,
        sequence=sequence,
        transcript=transcript,
        duration_seconds=duration,
    )
    await add_segment(db, segment)

    next_event_sequence = len(lecture.events) + 1

    updated_topics = list(existing_topics)
    topic_data = extraction.get("topic")
    if topic_data and topic_data.get("is_new"):
        new_topic = LectureEventModel(
            lecture_id=lecture_id,
            type=LectureEventType.TOPIC,
            content=topic_data["name"],
            sequence=next_event_sequence,
        )
        await add_event(db, new_topic)
        updated_topics.append(topic_data["name"])
        next_event_sequence += 1

    updated_alerts: list[dict] = [
        {"message": e.content, "severity": e.severity}
        for e in lecture.events
        if e.type == LectureEventType.ALERT
    ]
    alert_data = extraction.get("alert")
    if alert_data:
        new_alert = LectureEventModel(
            lecture_id=lecture_id,
            type=LectureEventType.ALERT,
            content=alert_data["message"],
            severity=LectureEventSeverity(alert_data.get("severity", LectureEventSeverity.WARNING)),
            sequence=next_event_sequence,
        )
        await add_event(db, new_alert)
        updated_alerts.append({"message": alert_data["message"], "severity": alert_data.get("severity", "WARNING")})

    new_mindmap = await update_mindmap(
        transcript=transcript,
        topics=updated_topics,
        alerts=updated_alerts,
        current_mindmap=lecture.mindmap_markdown,
        lecture_title=lecture.title,
    )
    lecture.mindmap_markdown = new_mindmap

    await db.commit()
    return ProcessSegmentResponseSchema(
        segment=LectureSegmentSchema.model_validate(segment),
        mindmap_markdown=new_mindmap,
    )


async def generate_final_summary(db: AsyncSession, *, lecture_id: UUID) -> None:
    lecture = await get_lecture_with_relations(db, lecture_id)
    if not lecture:
        return

    segments_sorted = sorted(lecture.segments, key=lambda s: s.sequence)
    full_transcript = "\n\n".join(
        f"[Segmento {s.sequence}]\n{s.transcript}" for s in segments_sorted
    )
    topics = [e.content for e in lecture.events if e.type == LectureEventType.TOPIC]
    alerts = [
        {"message": e.content, "severity": e.severity}
        for e in lecture.events
        if e.type == LectureEventType.ALERT
    ]

    result = await generate_final_mindmap_and_summary(
        full_transcript=full_transcript,
        topics=topics,
        alerts=alerts,
        lecture_title=lecture.title,
    )

    lecture.summary = result["summary"]
    if result["mindmap_markdown"]:
        lecture.mindmap_markdown = result["mindmap_markdown"]

    await db.commit()
