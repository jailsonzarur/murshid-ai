from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.features.subjects.models import SubjectDocumentStatus


class SubjectSchema(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UpdateSubjectSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class DeleteSubjectResponse(BaseModel):
    subject_id: UUID
    message: str


class SubjectDocumentSchema(BaseModel):
    id: UUID
    subject_id: UUID
    title: str
    original_name: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    status: SubjectDocumentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteSubjectDocumentResponse(BaseModel):
    document_id: UUID
    message: str


class SubjectDetailSchema(SubjectSchema):
    documents: list[SubjectDocumentSchema] = []
