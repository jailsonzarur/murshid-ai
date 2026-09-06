from __future__ import annotations

import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy import Enum as SQLEnum
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
    status: Mapped[SubjectDocumentStatus] = mapped_column(
        SQLEnum(SubjectDocumentStatus, native_enum=False),
        nullable=False,
        default=SubjectDocumentStatus.PENDING,
    )
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    subject: Mapped[SubjectModel] = relationship("SubjectModel", back_populates="documents")

    def __repr__(self) -> str:
        return f"<SubjectDocumentModel(id={self.id}, title={self.title})>"
