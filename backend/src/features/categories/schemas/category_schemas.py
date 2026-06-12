from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategorySchema(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class CreateCategorySchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UpdateCategorySchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class DeleteCategoryResponse(BaseModel):
    category_id: UUID
    message: str
