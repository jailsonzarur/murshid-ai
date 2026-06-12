from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.features.categories.schemas.category_schemas import CategorySchema
from src.features.lectures.models import LectureEventSeverity, LectureEventType, LectureStatus


class StartLectureSchema(BaseModel):
    title: str | None = None
    category_id: UUID | None = None


class LectureEventSchema(BaseModel):
    id: UUID
    type: LectureEventType
    content: str
    severity: LectureEventSeverity | None = None
    sequence: int
    offset_seconds: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LectureSegmentSchema(BaseModel):
    id: UUID
    sequence: int
    transcript: str
    duration_seconds: float
    offset_seconds: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessSegmentResponseSchema(BaseModel):
    segment: LectureSegmentSchema
    new_events: list[LectureEventSchema]
    mindmap_markdown: str | None = None


class LectureSummarySchema(BaseModel):
    id: UUID
    user_id: UUID
    category: CategorySchema | None = None
    title: str | None = None
    status: LectureStatus
    duration_seconds: float
    topics_count: int
    alerts_count: int
    mindmap_markdown: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LectureDetailSchema(BaseModel):
    id: UUID
    user_id: UUID
    category: CategorySchema | None = None
    title: str | None = None
    status: LectureStatus
    duration_seconds: float
    summary: str | None = None
    mindmap_markdown: str | None = None
    events: list[LectureEventSchema]
    segments: list[LectureSegmentSchema]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
