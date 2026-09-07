from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.features.files.services.bucket_service import get_bucket_service
from src.features.subjects.models import SubjectDocumentModel, SubjectDocumentStatus


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
    thumbnail_url: str | None = None
    icon_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, document: SubjectDocumentModel) -> SubjectDocumentSchema:
        schema = cls.model_validate(document)
        bucket = get_bucket_service()
        if document.thumbnail_key:
            schema.thumbnail_url = bucket.get_presigned_url(document.thumbnail_key)
        if document.icon_key:
            schema.icon_url = bucket.get_presigned_url(document.icon_key)
        return schema


class DeleteSubjectDocumentResponse(BaseModel):
    document_id: UUID
    message: str


class SubjectDetailSchema(SubjectSchema):
    documents: list[SubjectDocumentSchema] = []
