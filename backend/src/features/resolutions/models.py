from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.features.users.models import UserModel

if TYPE_CHECKING:
    from src.features.exams.models import ExamModel
    from src.features.questions.models import OptionModel, QuestionModel


class ExamResolutionMode(enum.StrEnum):
    EXAM = "EXAM"
    STUDY = "STUDY"


class ExamResolutionStatus(enum.StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    SUBMITTED = "SUBMITTED"
    GRADED = "GRADED"
    ERROR = "ERROR"


class ExamResolutionResult(enum.StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"


class ResponseEvaluationSource(enum.StrEnum):
    AUTO = "AUTO"
    AI = "AI"
    MANUAL = "MANUAL"


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExamResolutionModel(Base):
    __tablename__ = "exam_resolutions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    exam_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exams.id"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    mode: Mapped[ExamResolutionMode] = mapped_column(SQLEnum(ExamResolutionMode, native_enum=False), nullable=False)
    status: Mapped[ExamResolutionStatus] = mapped_column(
        SQLEnum(ExamResolutionStatus, native_enum=False),
        nullable=False,
        default=ExamResolutionStatus.IN_PROGRESS,
    )
    result: Mapped[ExamResolutionResult | None] = mapped_column(
        SQLEnum(ExamResolutionResult, native_enum=False),
        nullable=True,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    exam: Mapped[ExamModel] = relationship("ExamModel")
    user: Mapped[UserModel] = relationship(UserModel)
    responses: Mapped[list[QuestionResponseModel]] = relationship(
        "QuestionResponseModel",
        back_populates="resolution",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1)", name="ck_exam_resolutions_score_range"),
        CheckConstraint("time_spent_seconds >= 0", name="ck_exam_resolutions_time_spent_non_negative"),
    )


class QuestionResponseModel(Base):
    __tablename__ = "question_responses"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    resolution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exam_resolutions.id"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=False,
        index=True,
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    resolution: Mapped[ExamResolutionModel] = relationship("ExamResolutionModel", back_populates="responses")
    question: Mapped[QuestionModel] = relationship("QuestionModel")
    items: Mapped[list[QuestionResponseItemModel]] = relationship(
        "QuestionResponseItemModel",
        back_populates="response",
        cascade="all, delete-orphan",
    )
    evaluations: Mapped[list[QuestionResponseEvaluationModel]] = relationship(
        "QuestionResponseEvaluationModel",
        back_populates="response",
        cascade="all, delete-orphan",
        order_by="QuestionResponseEvaluationModel.evaluated_at.desc()",
    )


class QuestionResponseItemModel(Base):
    __tablename__ = "question_response_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    response_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("question_responses.id"),
        nullable=False,
        index=True,
    )
    option_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("options.id"), nullable=True)
    text_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    response: Mapped[QuestionResponseModel] = relationship("QuestionResponseModel", back_populates="items")
    option: Mapped[OptionModel | None] = relationship("OptionModel")


class QuestionResponseEvaluationModel(Base):
    __tablename__ = "question_response_evaluations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    response_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("question_responses.id"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_source: Mapped[ResponseEvaluationSource] = mapped_column(
        SQLEnum(ResponseEvaluationSource, native_enum=False),
        nullable=False,
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    response: Mapped[QuestionResponseModel] = relationship("QuestionResponseModel", back_populates="evaluations")

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 1", name="ck_question_response_evaluations_score_range"),
    )
