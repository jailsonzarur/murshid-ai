from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.features.exams.models import ExamStatus


class ExamListSchema(BaseModel):
    id: Annotated[UUID, Field(description="Exam ID")]
    name: Annotated[str, Field(description="Exam name")]
    general_subject: Annotated[str | None, Field(description="General subject")]
    status: Annotated[ExamStatus, Field(description="Processing status")]
    documents_count: Annotated[int, Field(description="Number of uploaded documents")]
    created_at: Annotated[datetime, Field(description="Creation date")]
    updated_at: Annotated[datetime, Field(description="Last update date")]

    model_config = ConfigDict(from_attributes=True)


class ExamUploadResponse(BaseModel):
    exam_id: UUID
    message: str


class ExamDeleteResponse(BaseModel):
    exam_id: UUID
    message: str


class ExamViewerOptionSchema(BaseModel):
    id: UUID
    text: str
    letter: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ExamViewerQuestionSchema(BaseModel):
    id: UUID
    type: Literal["OBJECTIVE", "SUBJECTIVE"]
    statement: str
    image_url: str | None = None
    options: list[ExamViewerOptionSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RawQuestionSchema(BaseModel):
    raw_text: str
    box_ids: list[int] = Field(default_factory=list)
    exam_order: int


class RawExamExtractionSchema(BaseModel):
    questions: list[RawQuestionSchema]


class OptionSchema(BaseModel):
    text: str
    letter: str | None = None
    is_correct: bool | None = None


class QuestionSchema(BaseModel):
    statement: str
    type: Literal["OBJECTIVE", "SUBJECTIVE"]
    category_name: str
    box_ids: list[int] = Field(default_factory=list)
    exam_order: int
    options: list[OptionSchema] = Field(default_factory=list)


class ExamExtractionSchema(BaseModel):
    questions: list[QuestionSchema]
