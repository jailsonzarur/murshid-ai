from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<CategoryModel(id={self.id}, name={self.name})>"
