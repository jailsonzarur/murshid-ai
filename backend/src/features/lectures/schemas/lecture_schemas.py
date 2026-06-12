from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.features.lectures.models import LectureEventSeverity, LectureEventType, LectureStatus


class StartLectureSchema(BaseModel):
    title: str | None = None


class LectureEventSchema(BaseModel):
    id: UUID
    type: LectureEventType
    content: str
    severity: LectureEventSeverity | None = None
    sequence: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LectureSegmentSchema(BaseModel):
    id: UUID
    sequence: int
    transcript: str
    duration_seconds: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessSegmentResponseSchema(BaseModel):
    segment: LectureSegmentSchema
    mindmap_markdown: str | None = None


class LectureSummarySchema(BaseModel):
    id: UUID
    user_id: UUID
    title: str | None = None
    status: LectureStatus
    mindmap_markdown: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LectureDetailSchema(BaseModel):
    id: UUID
    user_id: UUID
    title: str | None = None
    status: LectureStatus
    summary: str | None = None
    mindmap_markdown: str | None = None
    events: list[LectureEventSchema]
    segments: list[LectureSegmentSchema]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
