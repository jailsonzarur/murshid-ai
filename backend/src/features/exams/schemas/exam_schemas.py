import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Form, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.features.exams.models import ExamStatus


class ExamListSchema(BaseModel):
    id: Annotated[UUID, Field(description="ID da prova")]
    name: Annotated[str, Field(description="Nome da prova")]
    general_subject: Annotated[str | None, Field(description="Assunto geral")]
    status: Annotated[ExamStatus, Field(description="Status de processamento")]
    documents_count: Annotated[int, Field(description="Número de documentos enviados")]
    created_at: Annotated[datetime, Field(description="Data de criação")]
    updated_at: Annotated[datetime, Field(description="Data da última atualização")]

    model_config = ConfigDict(from_attributes=True)


class ExamUploadResponse(BaseModel):
    exam_id: UUID
    message: str


class ExamUploadFileOrderItemSchema(BaseModel):
    client_id: str
    file_name: str
    page_order: int


class ExamUploadFormSchema(BaseModel):
    name: str
    general_subject: str | None = None
    file_order: list[ExamUploadFileOrderItemSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_file_order(self) -> "ExamUploadFormSchema":
        if not self.file_order:
            return self

        self.file_order.sort(key=lambda item: item.page_order)
        page_orders = [item.page_order for item in self.file_order]

        if page_orders != list(range(1, len(self.file_order) + 1)):
            raise ValueError("Ordem dos arquivos inválida.")

        return self

    @classmethod
    def as_form(
        cls,
        name: Annotated[str, Form(...)],
        general_subject: Annotated[str | None, Form()] = None,
        file_order: Annotated[str | None, Form()] = None,
    ) -> "ExamUploadFormSchema":
        if not file_order:
            return cls(name=name, general_subject=general_subject)

        try:
            raw_file_order = json.loads(file_order)
            return cls(
                name=name,
                general_subject=general_subject,
                file_order=[ExamUploadFileOrderItemSchema.model_validate(item) for item in raw_file_order],
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "errors": ["Ordem dos arquivos inválida."], "data": None},
            ) from exc


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
