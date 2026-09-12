from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.lectures.models import LectureModel, LectureStatus, MindmapStatus
from src.features.lectures.services import lecture_service


@pytest.fixture
def dispatched(monkeypatch) -> list[str]:
    calls: list[str] = []

    class _Task:
        def delay(self, lecture_id: str) -> None:
            calls.append(lecture_id)

    import src.features.lectures.tasks as tasks

    monkeypatch.setattr(tasks, "generate_lecture_mindmap_task", _Task())
    return calls


@pytest_asyncio.fixture
async def lecture(db_session: AsyncSession, test_user: dict) -> LectureModel:
    model = LectureModel(
        user_id=test_user["id"],
        title="Aula",
        status=LectureStatus.COMPLETED,
        summary="Um resumo pronto.",
    )
    db_session.add(model)
    await db_session.commit()
    return model


@pytest.mark.asyncio
class TestRequestMindmap:
    async def test_the_first_request_claims_and_dispatches(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        await lecture_service.request_mindmap(db_session, lecture.id, test_user["id"])

        await db_session.refresh(lecture)
        assert lecture.mindmap_status == MindmapStatus.REQUESTED
        assert dispatched == [str(lecture.id)]

    async def test_a_second_request_does_not_dispatch_again(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        await lecture_service.request_mindmap(db_session, lecture.id, test_user["id"])
        await lecture_service.request_mindmap(db_session, lecture.id, test_user["id"])
        await lecture_service.request_mindmap(db_session, lecture.id, test_user["id"])

        assert dispatched == [str(lecture.id)]

    async def test_a_failed_mindmap_can_be_requested_again(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        await lecture_service.request_mindmap(db_session, lecture.id, test_user["id"])
        lecture.mindmap_status = MindmapStatus.FAILED
        await db_session.commit()

        await lecture_service.request_mindmap(db_session, lecture.id, test_user["id"])

        assert dispatched == [str(lecture.id), str(lecture.id)]

    async def test_a_lecture_without_summary_is_rejected(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict, dispatched
    ):
        lecture.summary = None
        await db_session.commit()

        with pytest.raises(HTTPException) as exc:
            await lecture_service.request_mindmap(db_session, lecture.id, test_user["id"])

        assert exc.value.status_code == 400
        assert dispatched == []

    async def test_another_user_gets_a_404(
        self, db_session: AsyncSession, lecture: LectureModel, dispatched
    ):
        from uuid import uuid4

        with pytest.raises(HTTPException) as exc:
            await lecture_service.request_mindmap(db_session, lecture.id, uuid4())

        assert exc.value.status_code == 404
        assert dispatched == []
