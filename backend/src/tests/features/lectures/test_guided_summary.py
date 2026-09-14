from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.lectures.ai.guided_summary_agent import drop_unknown_citations
from src.features.lectures.models import GuidedSummaryStatus, LectureModel, LectureStatus
from src.features.lectures.services.lecture_service import request_guided_summary
from src.features.subjects.models import SubjectModel


@pytest.fixture
def dispatched(monkeypatch) -> list[str]:
    calls: list[str] = []

    class _Task:
        def delay(self, lecture_id: str) -> None:
            calls.append(lecture_id)

    import src.features.lectures.tasks as tasks

    monkeypatch.setattr(tasks, "generate_lecture_guided_summary_task", _Task())
    return calls


@pytest_asyncio.fixture
async def lecture(db_session: AsyncSession, test_user: dict) -> LectureModel:
    subject = SubjectModel(user_id=test_user["id"], name="Microbiologia")
    db_session.add(subject)
    await db_session.flush()

    model = LectureModel(
        user_id=test_user["id"],
        title="Aula",
        status=LectureStatus.COMPLETED,
        summary="Um resumo pronto.",
        subject_id=subject.id,
    )
    db_session.add(model)
    await db_session.commit()
    return model


@pytest.mark.asyncio
class TestRequestGuidedSummary:
    async def test_the_first_request_claims_and_dispatches(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        await request_guided_summary(db_session, lecture.id, test_user["id"])

        await db_session.refresh(lecture)
        assert lecture.guided_status == GuidedSummaryStatus.REQUESTED
        assert dispatched == [str(lecture.id)]

    async def test_a_second_request_does_not_dispatch_again(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        await request_guided_summary(db_session, lecture.id, test_user["id"])
        await request_guided_summary(db_session, lecture.id, test_user["id"])

        assert dispatched == [str(lecture.id)]

    async def test_a_failed_run_can_be_requested_again(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        await request_guided_summary(db_session, lecture.id, test_user["id"])
        lecture.guided_status = GuidedSummaryStatus.FAILED
        await db_session.commit()

        await request_guided_summary(db_session, lecture.id, test_user["id"])

        assert dispatched == [str(lecture.id), str(lecture.id)]

    async def test_a_lecture_already_guided_is_left_alone(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        lecture.guided_summary = "ja existe"
        await db_session.commit()

        await request_guided_summary(db_session, lecture.id, test_user["id"])

        assert dispatched == []

    async def test_a_lecture_without_summary_is_rejected(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        lecture.summary = None
        await db_session.commit()

        with pytest.raises(HTTPException) as exc:
            await request_guided_summary(db_session, lecture.id, test_user["id"])

        assert exc.value.status_code == 400
        assert dispatched == []

    async def test_a_lecture_without_subject_is_rejected(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        lecture.subject_id = None
        await db_session.commit()

        with pytest.raises(HTTPException) as exc:
            await request_guided_summary(db_session, lecture.id, test_user["id"])

        assert exc.value.status_code == 400
        assert dispatched == []

    async def test_another_user_gets_a_404(
        self, db_session: AsyncSession, lecture: LectureModel, dispatched
    ):
        with pytest.raises(HTTPException) as exc:
            await request_guided_summary(db_session, lecture.id, uuid4())

        assert exc.value.status_code == 404
        assert dispatched == []


class TestCitationValidation:
    def test_known_citations_survive(self):
        texto = "A parede é espessa [[1]] e retém o corante [[2]]."

        assert drop_unknown_citations(texto, {1, 2}) == texto

    def test_an_invented_citation_is_removed(self):
        texto = "A parede é espessa [[1]] e retém o corante [[7]]."

        assert drop_unknown_citations(texto, {1, 2}) == "A parede é espessa [[1]] e retém o corante ."

    def test_text_without_citations_is_untouched(self):
        texto = "Nenhuma citação aqui."

        assert drop_unknown_citations(texto, set()) == texto
