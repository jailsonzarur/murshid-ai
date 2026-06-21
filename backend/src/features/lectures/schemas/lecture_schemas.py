from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.features.categories.schemas.category_schemas import CategorySchema
from src.features.lectures.models import LectureStatus


class StartLectureSchema(BaseModel):
    title: str | None = None
    category_id: UUID | None = None


class LectureNodeSchema(BaseModel):
    id: str
    parent_id: str | None = None
    label: str
    summary: str | None = None


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
    insight_message: str | None = None


class LectureSummarySchema(BaseModel):
    id: UUID
    user_id: UUID
    category: CategorySchema | None = None
    title: str | None = None
    status: LectureStatus
    duration_seconds: float
    nodes_count: int
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
    nodes: list[LectureNodeSchema]
    segments: list[LectureSegmentSchema]
    created_at: datetime
    updated_at: datetime
