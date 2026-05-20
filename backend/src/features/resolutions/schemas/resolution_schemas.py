from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.features.resolutions.models import (
    ExamResolutionMode,
    ExamResolutionResult,
    ExamResolutionStatus,
    ResponseEvaluationSource,
)


class CreateResolutionSchema(BaseModel):
    mode: ExamResolutionMode


class ResponseItemInputSchema(BaseModel):
    option_id: UUID | None = None
    text_answer: str | None = None


class UpsertQuestionResponseSchema(BaseModel):
    items: list[ResponseItemInputSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_items(self) -> UpsertQuestionResponseSchema:
        if not self.items:
            raise ValueError("Informe ao menos uma resposta.")

        return self


class ResolutionSummarySchema(BaseModel):
    id: UUID
    exam_id: UUID
    user_id: UUID
    mode: ExamResolutionMode
    status: ExamResolutionStatus
    result: ExamResolutionResult | None = None
    score: float | None = None
    started_at: datetime
    paused_at: datetime | None = None
    submitted_at: datetime | None = None
    graded_at: datetime | None = None
    time_spent_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResolutionOptionSchema(BaseModel):
    id: UUID
    text: str
    letter: str | None = None


class ResolutionQuestionSchema(BaseModel):
    id: UUID
    type: str
    statement: str
    image_url: str | None = None
    explanation: str | None = None
    expected_answer: str | None = None
    exam_order: int
    options: list[ResolutionOptionSchema] = Field(default_factory=list)


class QuestionResponseItemSchema(BaseModel):
    id: UUID
    option_id: UUID | None = None
    text_answer: str | None = None


class QuestionResponseEvaluationSchema(BaseModel):
    id: UUID
    score: float
    feedback: str | None = None
    evaluation_source: ResponseEvaluationSource
    evaluated_at: datetime
    model_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ResolutionEvaluationTaskSchema(BaseModel):
    task_id: str
    resolution: ResolutionSummarySchema


class QuestionResponseSchema(BaseModel):
    id: UUID
    question_id: UUID
    answered_at: datetime | None = None
    items: list[QuestionResponseItemSchema] = Field(default_factory=list)
    evaluation: QuestionResponseEvaluationSchema | None = None


class ResolutionQuestionDetailSchema(BaseModel):
    question: ResolutionQuestionSchema
    response: QuestionResponseSchema | None = None


class ResolutionDetailSchema(BaseModel):
    resolution: ResolutionSummarySchema
    questions: list[ResolutionQuestionDetailSchema]
    can_show_evaluations: bool


class ResolutionSubmitSchema(BaseModel):
    resolution: ResolutionSummarySchema
