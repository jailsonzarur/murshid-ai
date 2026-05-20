from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from decouple import config
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class EvaluationOption:
    key: str
    text: str
    letter: str | None = None
    is_correct: bool | None = None


@dataclass(frozen=True)
class UserAnswerItem:
    text_answer: str | None = None
    option_key: str | None = None
    option_letter: str | None = None
    option_text: str | None = None


@dataclass(frozen=True)
class AnswerKeyInference:
    correct_option_keys: list[str]
    explanation: str | None = None
    expected_answer: str | None = None
    model_name: str | None = None
    raw_output: str | None = None


@dataclass(frozen=True)
class UserResponseEvaluation:
    score: float
    feedback: str
    evaluation_source: str
    model_name: str | None = None
    raw_output: str | None = None


class AnswerKeyInferenceOutput(BaseModel):
    correct_option_keys: list[str] = Field(default_factory=list)
    explanation: str | None = Field(
        default=None,
        description="Explicação obrigatoriamente em português do Brasil.",
    )
    expected_answer: str | None = Field(
        default=None,
        description="Resposta esperada obrigatoriamente em português do Brasil.",
    )


class UserResponseEvaluationOutput(BaseModel):
    score: float = Field(ge=0, le=1)
    feedback: str = Field(
        min_length=1,
        description="Feedback obrigatoriamente em português do Brasil, direto, específico e em Markdown simples.",
    )


async def infer_question_answer_key(
    *,
    question_type: str,
    statement: str,
    options: list[EvaluationOption],
) -> AnswerKeyInference:
    from langchain_core.messages import HumanMessage

    model_name, llm = _get_structured_llm(AnswerKeyInferenceOutput)
    result = await llm.ainvoke(
        [
            HumanMessage(
                content=_build_answer_key_prompt(
                    question_type=question_type,
                    statement=statement,
                    options=options,
                )
            )
        ]
    )
    parsed = result if isinstance(result, AnswerKeyInferenceOutput) else AnswerKeyInferenceOutput.model_validate(result)

    return AnswerKeyInference(
        correct_option_keys=parsed.correct_option_keys,
        explanation=parsed.explanation,
        expected_answer=parsed.expected_answer,
        model_name=model_name,
        raw_output=parsed.model_dump_json(),
    )


async def evaluate_user_response(
    *,
    question_type: str,
    statement: str,
    options: list[EvaluationOption],
    student_answer: list[UserAnswerItem],
    expected_answer: str | None = None,
    explanation: str | None = None,
) -> UserResponseEvaluation:
    if question_type in {"OBJECTIVE_SINGLE", "OBJECTIVE_MULTI"}:
        correct_options = [option for option in options if option.is_correct]
        if correct_options:
            selected_keys = {item.option_key for item in student_answer if item.option_key}
            correct_keys = {option.key for option in correct_options}
            score = 1.0 if selected_keys == correct_keys else 0.0
            correct_labels = ", ".join(option.letter or option.text for option in correct_options)
            feedback = _ensure_portuguese_auto_feedback(explanation, correct_labels)
            return UserResponseEvaluation(score=score, feedback=feedback, evaluation_source="AUTO")

    from langchain_core.messages import HumanMessage

    model_name, llm = _get_structured_llm(UserResponseEvaluationOutput)
    result = await llm.ainvoke(
        [
            HumanMessage(
                content=_build_user_response_evaluation_prompt(
                    question_type=question_type,
                    statement=statement,
                    options=options,
                    student_answer=student_answer,
                    expected_answer=expected_answer,
                    explanation=explanation,
                )
            )
        ]
    )
    parsed = (
        result
        if isinstance(result, UserResponseEvaluationOutput)
        else UserResponseEvaluationOutput.model_validate(result)
    )

    return UserResponseEvaluation(
        score=parsed.score,
        feedback=parsed.feedback,
        evaluation_source="AI",
        model_name=model_name,
        raw_output=parsed.model_dump_json(),
    )


def _get_structured_llm(output_schema: type[BaseModel]) -> tuple[str, Any]:
    from langchain_openai import ChatOpenAI

    default_model = config("EXAM_TEXT_MODEL", default=config("OPENAI_TEXT_MODEL", default="gpt-4o"))
    model_name = str(config("EXAM_GRADING_MODEL", default=default_model))
    api_key = str(config("OPENAI_API_KEY", default="")).strip()
    kwargs: dict[str, Any] = {"model": model_name, "temperature": 0}

    if api_key:
        kwargs["api_key"] = api_key

    return model_name, ChatOpenAI(**kwargs).with_structured_output(output_schema)


def _build_answer_key_prompt(
    *,
    question_type: str,
    statement: str,
    options: list[EvaluationOption],
) -> str:
    payload = {
        "question_type": question_type,
        "statement": statement,
        "options_or_subitems": [_serialize_option(option) for option in options],
    }

    return (
        "Você está criando o gabarito de uma questão de prova.\n"
        "Responda todos os campos textuais obrigatoriamente em português do Brasil.\n"
        "Não use marcações visuais de uma prova escaneada como evidência de resposta correta; resolva a questão "
        "apenas pelo enunciado e pelas alternativas/subitens.\n\n"
        "Regras:\n"
        "- Para OBJECTIVE_SINGLE, retorne exatamente uma correct_option_key.\n"
        "- Para OBJECTIVE_MULTI, retorne todas as correct_option_keys corretas.\n"
        "- Para SUBJECTIVE, retorne correct_option_keys vazio e crie expected_answer com os pontos essenciais "
        "para corrigir respostas de alunos.\n"
        "- Em explanation, explique de forma objetiva por que a resposta correta é correta e, quando houver "
        "alternativas, por que as demais não são.\n\n"
        f"QUESTION PAYLOAD:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _build_user_response_evaluation_prompt(
    *,
    question_type: str,
    statement: str,
    options: list[EvaluationOption],
    student_answer: list[UserAnswerItem],
    expected_answer: str | None,
    explanation: str | None,
) -> str:
    payload = {
        "question_type": question_type,
        "statement": statement,
        "options_or_subitems": [_serialize_option(option) for option in options],
        "expected_answer": expected_answer,
        "explanation": explanation,
        "student_answer": [
            {
                "text_answer": answer.text_answer,
                "option_key": answer.option_key,
                "option_letter": answer.option_letter,
                "option_text": answer.option_text,
            }
            for answer in student_answer
        ],
    }

    return (
        "Você está corrigindo a resposta de um aluno para uma questão de prova.\n"
        "Responda obrigatoriamente em português do Brasil.\n"
        "Retorne um score entre 0 e 1 e um feedback específico.\n\n"
        "Critérios de correção:\n"
        "- Compare a resposta do aluno com expected_answer e explanation quando estiverem disponíveis.\n"
        "- Se for questão objetiva sem gabarito determinístico, resolva a questão pelo enunciado e alternativas "
        "antes de comparar com a resposta do aluno.\n"
        "- Se for questão subjetiva, atribua nota proporcional: 1.0 para resposta completa, 0.5 para resposta "
        "parcial relevante, 0.0 para resposta incorreta, vazia ou sem relação com o esperado.\n"
        "- Não seja excessivamente generoso. A nota deve refletir o quanto a resposta realmente atende aos "
        "pontos essenciais.\n"
        "- No feedback, diga objetivamente o que está correto, o que faltou ou por que está errado. Não invente "
        "informações fora do enunciado/base esperada.\n\n"
        "Formato do feedback:\n"
        "- Use Markdown simples e válido.\n"
        "- Comece com uma frase curta em negrito resumindo o resultado.\n"
        "- Quando houver mais de um ponto, use lista com bullets.\n"
        "- Não use HTML, tabelas ou headings.\n\n"
        f"QUESTION PAYLOAD:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _serialize_option(option: EvaluationOption) -> dict[str, str | bool | None]:
    return {
        "key": option.key,
        "letter": option.letter,
        "text": option.text,
        "is_correct": option.is_correct,
    }


def _ensure_portuguese_auto_feedback(explanation: str | None, correct_labels: str) -> str:
    if explanation:
        return explanation

    return f"**Resposta correta:** {correct_labels}."
