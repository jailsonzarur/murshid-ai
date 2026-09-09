from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
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

if TYPE_CHECKING:
    from src.features.subjects.models import SubjectModel


class LectureAudioStatus(enum.StrEnum):
    PENDING = "PENDING"
    CHUNKING = "CHUNKING"
    TRANSCRIBING = "TRANSCRIBING"
    DONE = "DONE"
    FAILED = "FAILED"


class LectureStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def utc_now() -> datetime:
    return datetime.now(UTC)


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
    subject_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LectureStatus] = mapped_column(
        SQLEnum(LectureStatus, native_enum=False), nullable=False, default=LectureStatus.ACTIVE
    )
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    mindmap_data: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    subject: Mapped[SubjectModel | None] = relationship("SubjectModel", lazy="selectin")
    segments: Mapped[list[LectureSegmentModel]] = relationship(
        back_populates="lecture",
        cascade="all, delete-orphan",
        order_by=LectureSegmentModel.sequence,
    )

    def __repr__(self) -> str:
        return f"<LectureModel(id={self.id}, status={self.status})>"


class LectureAudioModel(Base):
    __tablename__ = "lecture_audios"
    __table_args__ = (
        UniqueConstraint("lecture_id", "sequence", name="uq_lecture_audios_lecture_id_sequence"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    lecture_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[LectureAudioStatus] = mapped_column(
        SQLEnum(LectureAudioStatus, native_enum=False),
        nullable=False,
        default=LectureAudioStatus.PENDING,
    )
    transcribed_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    chunks: Mapped[list[LectureAudioChunkModel]] = relationship(
        back_populates="audio",
        cascade="all, delete-orphan",
        order_by="LectureAudioChunkModel.sequence",
    )

    def __repr__(self) -> str:
        return f"<LectureAudioModel(id={self.id}, status={self.status})>"


class LectureAudioChunkModel(Base):
    __tablename__ = "lecture_audio_chunks"
    __table_args__ = (
        UniqueConstraint("audio_id", "sequence", name="uq_lecture_audio_chunks_audio_id_sequence"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    audio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("lecture_audios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    audio: Mapped[LectureAudioModel] = relationship("LectureAudioModel", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<LectureAudioChunkModel(id={self.id}, sequence={self.sequence})>"
