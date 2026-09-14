from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.features.lectures.models import GuidedSummaryStatus, LectureStatus, MindmapStatus
from src.features.subjects.schemas.subject_schemas import SubjectSchema


class StartLectureSchema(BaseModel):
    title: str | None = None
    subject_id: UUID | None = None


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
    subject: SubjectSchema | None = None
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
    subject: SubjectSchema | None = None
    title: str | None = None
    status: LectureStatus
    duration_seconds: float
    summary: str | None = None
    mindmap_status: MindmapStatus
    guided_summary: str | None = None
    guided_status: GuidedSummaryStatus
    nodes: list[LectureNodeSchema]
    segments: list[LectureSegmentSchema]
    created_at: datetime
    updated_at: datetime


class UpdateLectureSubjectSchema(BaseModel):
    subject_id: UUID | None = None


class GuidedCitationExcerptSchema(BaseModel):
    n: int
    chunk_id: UUID
    distance: float
    heading_path: str
    page_start: int | None = None
    text: str


class GuidedCitationSchema(BaseModel):
    topic: str
    excerpts: list[GuidedCitationExcerptSchema]
