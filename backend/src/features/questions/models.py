from __future__ import annotations

import enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.features.categories.models import CategoryModel
    from src.features.exams.models import ExamModel


class QuestionType(enum.StrEnum):
    OBJECTIVE = "OBJECTIVE"
    SUBJECTIVE = "SUBJECTIVE"


class QuestionModel(Base):
    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    exam_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exams.id"), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True,
    )
    type: Mapped[QuestionType] = mapped_column(SQLEnum(QuestionType, native_enum=False), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_order: Mapped[int] = mapped_column(Integer, nullable=False)

    exam: Mapped[ExamModel] = relationship("ExamModel", back_populates="questions")
    category: Mapped[CategoryModel | None] = relationship("CategoryModel", back_populates="questions")
    options: Mapped[list[OptionModel]] = relationship(
        "OptionModel",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<QuestionModel(id={self.id}, exam_id={self.exam_id}, exam_order={self.exam_order})>"


class OptionModel(Base):
    __tablename__ = "options"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    letter: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    question: Mapped[QuestionModel] = relationship("QuestionModel", back_populates="options")

    def __repr__(self) -> str:
        return f"<OptionModel(id={self.id}, question_id={self.question_id}, letter={self.letter})>"
