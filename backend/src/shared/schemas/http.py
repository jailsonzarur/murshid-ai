from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: Annotated[bool, Field(default=True)]
    errors: Annotated[None, Field(default=None)]
    data: Annotated[T | None, Field(default=None)]


class ErrorResponse(BaseModel):
    success: Annotated[bool, Field(default=False)]
    errors: Annotated[list[str], Field(default_factory=list)]
    data: Annotated[None, Field(default=None)]
