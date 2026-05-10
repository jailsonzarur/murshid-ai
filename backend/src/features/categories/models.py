from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.features.questions.models import QuestionModel


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    questions: Mapped[list[QuestionModel]] = relationship("QuestionModel", back_populates="category")

    def __repr__(self) -> str:
        return f"<CategoryModel(id={self.id}, name={self.name})>"
