from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.exams.models import ExamModel, ExamStatus
from src.features.questions.models import OptionModel, QuestionModel, QuestionType


async def create_completed_exam(db_session: AsyncSession) -> tuple[ExamModel, QuestionModel, OptionModel]:
    exam = ExamModel(name="Prova de teste", general_subject="História", status=ExamStatus.COMPLETED)
    db_session.add(exam)
    await db_session.flush()

    question = QuestionModel(
        exam_id=exam.id,
        type=QuestionType.OBJECTIVE_SINGLE,
        statement="Qual alternativa está correta?",
        explanation="A alternativa A é a correta.",
        exam_order=1,
    )
    correct_option = OptionModel(text="Alternativa A", letter="A", is_correct=True)
    question.options.append(correct_option)
    question.options.append(OptionModel(text="Alternativa B", letter="B", is_correct=False))
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(exam)

    return exam, question, correct_option


def describe_resolution_flow():
    @pytest.mark.asyncio
    async def it_should_create_answer_pause_resume_and_submit_resolution(
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
    ):
        exam, question, correct_option = await create_completed_exam(db_session)

        create_response = await client.post(
            f"/exams/{exam.id}/resolutions",
            json={"mode": "EXAM"},
            headers=auth_headers,
        )

        assert create_response.status_code == 201
        resolution = create_response.json()["data"]
        resolution_id = UUID(resolution["id"])
        assert resolution["status"] == "IN_PROGRESS"

        active_response = await client.get(f"/exams/{exam.id}/resolutions/active", headers=auth_headers)

        assert active_response.status_code == 200
        assert active_response.json()["data"]["id"] == str(resolution_id)

        answer_response = await client.put(
            f"/resolutions/{resolution_id}/questions/{question.id}/response",
            json={"items": [{"option_id": str(correct_option.id)}]},
            headers=auth_headers,
        )

        assert answer_response.status_code == 200
        assert answer_response.json()["data"]["question_id"] == str(question.id)
        assert answer_response.json()["data"]["items"][0]["option_id"] == str(correct_option.id)

        detail_response = await client.get(f"/resolutions/{resolution_id}", headers=auth_headers)

        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["questions"][0]["response"]["question_id"] == str(question.id)

        pause_response = await client.post(f"/resolutions/{resolution_id}/pause", headers=auth_headers)

        assert pause_response.status_code == 200
        assert pause_response.json()["data"]["status"] == "PAUSED"

        resume_response = await client.post(f"/resolutions/{resolution_id}/resume", headers=auth_headers)

        assert resume_response.status_code == 200
        assert resume_response.json()["data"]["status"] == "IN_PROGRESS"

        submit_response = await client.post(f"/resolutions/{resolution_id}/submit", headers=auth_headers)

        assert submit_response.status_code == 200
        assert submit_response.json()["data"]["resolution"]["status"] == "SUBMITTED"

    @pytest.mark.asyncio
    async def it_should_evaluate_one_study_question_synchronously(
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
    ):
        exam, question, correct_option = await create_completed_exam(db_session)

        create_response = await client.post(
            f"/exams/{exam.id}/resolutions",
            json={"mode": "STUDY"},
            headers=auth_headers,
        )
        resolution_id = UUID(create_response.json()["data"]["id"])

        await client.put(
            f"/resolutions/{resolution_id}/questions/{question.id}/response",
            json={"items": [{"option_id": str(correct_option.id)}]},
            headers=auth_headers,
        )

        evaluation_response = await client.post(
            f"/resolutions/{resolution_id}/questions/{question.id}/evaluate",
            headers=auth_headers,
        )

        assert evaluation_response.status_code == 200
        data = evaluation_response.json()["data"]
        assert data["evaluation"]["score"] == 1.0
        assert data["evaluation"]["evaluation_source"] == "AUTO"

        submit_response = await client.post(f"/resolutions/{resolution_id}/submit", headers=auth_headers)

        assert submit_response.status_code == 200
        submitted_resolution = submit_response.json()["data"]["resolution"]
        assert submitted_resolution["status"] == "GRADED"
        assert submitted_resolution["score"] == 1.0
        assert submitted_resolution["result"] == "PASSED"
