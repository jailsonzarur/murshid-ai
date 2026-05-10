from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.features.questions.models import QuestionModel


class ExamStatus(enum.StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExamModel(Base):
    __tablename__ = "exams"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    general_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ExamStatus] = mapped_column(
        SQLEnum(ExamStatus, native_enum=False),
        nullable=False,
        default=ExamStatus.PENDING,
    )
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    documents: Mapped[list[ExamDocumentModel]] = relationship(
        "ExamDocumentModel",
        back_populates="exam",
        cascade="all, delete-orphan",
    )
    questions: Mapped[list[QuestionModel]] = relationship(
        "QuestionModel",
        back_populates="exam",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ExamModel(id={self.id}, name={self.name}, status={self.status})>"


class ExamDocumentModel(Base):
    __tablename__ = "exam_documents"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    exam_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exams.id"), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    page_order: Mapped[int] = mapped_column(Integer, nullable=False)

    exam: Mapped[ExamModel] = relationship("ExamModel", back_populates="documents")

    def __repr__(self) -> str:
        return f"<ExamDocumentModel(id={self.id}, exam_id={self.exam_id}, page_order={self.page_order})>"
