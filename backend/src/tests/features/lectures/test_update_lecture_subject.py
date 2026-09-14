from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.lectures.models import LectureModel, LectureStatus
from src.features.lectures.services.lecture_service import change_lecture_subject
from src.features.subjects.models import SubjectModel


@pytest_asyncio.fixture
async def subjects(db_session: AsyncSession, test_user: dict) -> list[SubjectModel]:
    created = [
        SubjectModel(user_id=test_user["id"], name="Microbiologia"),
        SubjectModel(user_id=test_user["id"], name="Imunologia"),
    ]
    db_session.add_all(created)
    await db_session.commit()
    return created


@pytest_asyncio.fixture
async def lecture(
    db_session: AsyncSession, test_user: dict, subjects: list[SubjectModel]
) -> LectureModel:
    model = LectureModel(
        user_id=test_user["id"],
        title="Aula",
        status=LectureStatus.COMPLETED,
        subject_id=subjects[0].id,
    )
    db_session.add(model)
    await db_session.commit()
    return model


@pytest.mark.asyncio
class TestChangeLectureSubject:
    async def test_swaps_to_another_subject(
        self, db_session: AsyncSession, lecture: LectureModel, subjects, test_user: dict
    ):
        detail = await change_lecture_subject(
            db_session, lecture.id, test_user["id"], subjects[1].id
        )

        assert detail.subject is not None
        assert detail.subject.name == "Imunologia"

    async def test_clears_the_subject_when_given_none(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict
    ):
        detail = await change_lecture_subject(db_session, lecture.id, test_user["id"], None)

        assert detail.subject is None

    async def test_a_lecture_from_another_user_is_not_found(
        self, db_session: AsyncSession, lecture: LectureModel, subjects
    ):
        with pytest.raises(HTTPException) as exc:
            await change_lecture_subject(db_session, lecture.id, uuid4(), subjects[1].id)

        assert exc.value.status_code == 404

    async def test_a_subject_from_another_user_is_rejected(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict
    ):
        outro = SubjectModel(user_id=uuid4(), name="De outro dono")
        db_session.add(outro)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc:
            await change_lecture_subject(db_session, lecture.id, test_user["id"], outro.id)

        assert exc.value.status_code == 404

    async def test_an_unknown_subject_is_rejected(
        self, db_session: AsyncSession, lecture: LectureModel, test_user: dict
    ):
        with pytest.raises(HTTPException) as exc:
            await change_lecture_subject(db_session, lecture.id, test_user["id"], uuid4())

        assert exc.value.status_code == 404
