from __future__ import annotations

import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class SubjectModel(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_subjects_user_id_name"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    documents: Mapped[list[SubjectDocumentModel]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="SubjectDocumentModel.created_at",
    )

    def __repr__(self) -> str:
        return f"<SubjectModel(id={self.id}, name={self.name})>"


EMBEDDING_DIMENSIONS = 1536


class SubjectDocumentIndexStatus(enum.StrEnum):
    NONE = "NONE"
    REQUESTED = "REQUESTED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class SubjectDocumentStatus(enum.StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class SubjectDocumentModel(Base):
    __tablename__ = "subject_documents"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[SubjectDocumentStatus] = mapped_column(
        SQLEnum(SubjectDocumentStatus, native_enum=False),
        nullable=False,
        default=SubjectDocumentStatus.PENDING,
    )
    index_status: Mapped[SubjectDocumentIndexStatus] = mapped_column(
        SQLEnum(SubjectDocumentIndexStatus, native_enum=False),
        nullable=False,
        default=SubjectDocumentIndexStatus.NONE,
    )
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    subject: Mapped[SubjectModel] = relationship("SubjectModel", back_populates="documents")

    def __repr__(self) -> str:
        return f"<SubjectDocumentModel(id={self.id}, title={self.title})>"


class SubjectDocumentChunkModel(Base):
    __tablename__ = "subject_document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "sequence", name="uq_subject_document_chunks_document_sequence"),
        Index("ix_subject_document_chunks_subject_id", "subject_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subject_documents.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    heading_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    def __repr__(self) -> str:
        return f"<SubjectDocumentChunkModel(id={self.id}, sequence={self.sequence})>"


class SubjectDocumentImageModel(Base):
    __tablename__ = "subject_document_images"
    __table_args__ = (Index("ix_subject_document_images_chunk_id", "chunk_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subject_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subject_document_chunks.id", ondelete="SET NULL"), nullable=True
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    def __repr__(self) -> str:
        return f"<SubjectDocumentImageModel(id={self.id}, page={self.page})>"
