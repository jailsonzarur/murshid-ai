from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.features.categories.models import CategoryModel


class LectureStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LectureEventType(enum.StrEnum):
    TOPIC = "TOPIC"
    ALERT = "ALERT"


class LectureEventSeverity(enum.StrEnum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


def utc_now() -> datetime:
    return datetime.now(UTC)


class LectureEventModel(Base):
    __tablename__ = "lecture_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    lecture_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lectures.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[LectureEventType] = mapped_column(
        SQLEnum(LectureEventType, native_enum=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[LectureEventSeverity | None] = mapped_column(
        SQLEnum(LectureEventSeverity, native_enum=False), nullable=True
    )
    offset_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    lecture: Mapped[LectureModel] = relationship("LectureModel", back_populates="events")

    def __repr__(self) -> str:
        return f"<LectureEventModel(id={self.id}, type={self.type}, sequence={self.sequence})>"


class LectureSegmentModel(Base):
    __tablename__ = "lecture_segments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    lecture_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lectures.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    offset_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    lecture: Mapped[LectureModel] = relationship("LectureModel", back_populates="segments")

    def __repr__(self) -> str:
        return f"<LectureSegmentModel(id={self.id}, sequence={self.sequence})>"


class LectureModel(Base):
    __tablename__ = "lectures"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LectureStatus] = mapped_column(
        SQLEnum(LectureStatus, native_enum=False), nullable=False, default=LectureStatus.ACTIVE
    )
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    mindmap_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    category: Mapped[CategoryModel | None] = relationship("CategoryModel", lazy="selectin")
    events: Mapped[list[LectureEventModel]] = relationship(
        back_populates="lecture",
        cascade="all, delete-orphan",
        order_by=LectureEventModel.sequence,
    )
    segments: Mapped[list[LectureSegmentModel]] = relationship(
        back_populates="lecture",
        cascade="all, delete-orphan",
        order_by=LectureSegmentModel.sequence,
    )

    def __repr__(self) -> str:
        return f"<LectureModel(id={self.id}, status={self.status})>"
