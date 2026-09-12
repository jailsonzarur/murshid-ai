from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, to_sync_url
from src.features.lectures.models import LectureModel, LectureSegmentModel, LectureStatus
from src.features.lectures.repository import (
    get_lecture_by_id_sync,
    get_lecture_with_segments_sync,
)
from src.features.users.models import UserModel


class TestSyncUrl:
    def test_postgres_becomes_psycopg2(self):
        assert (
            to_sync_url("postgresql+asyncpg://u:p@host:5432/db")
            == "postgresql+psycopg2://u:p@host:5432/db"
        )

    def test_sqlite_drops_the_async_driver(self):
        assert to_sync_url("sqlite+aiosqlite:///./api.db") == "sqlite:///./api.db"

    def test_an_unknown_scheme_is_left_alone(self):
        assert to_sync_url("mysql://host/db") == "mysql://host/db"

    def test_only_the_scheme_is_replaced(self):
        url = "postgresql+asyncpg://user:sqlite+aiosqlite@host/db"
        assert to_sync_url(url) == "postgresql+psycopg2://user:sqlite+aiosqlite@host/db"


@pytest.mark.asyncio
class TestSyncSessionSeesTheSameData:
    """Escreve pela sessão async e lê pela síncrona, no mesmo arquivo sqlite —
    prova que o sessionmaker novo enxerga os mesmos modelos e as mesmas linhas."""

    async def test_a_row_written_async_is_read_by_the_sync_session(self, tmp_path):
        async_url = f"sqlite+aiosqlite:///{tmp_path}/shared.db"
        async_engine = create_async_engine(async_url)
        sync_engine = create_engine(to_sync_url(async_url))

        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
        sync_session = sessionmaker(sync_engine, expire_on_commit=False)

        async with async_session() as db:
            user = UserModel(name="Dono", email="dono@example.com", password="x")
            db.add(user)
            await db.flush()

            lecture = LectureModel(
                user_id=user.id, title="Aula", status=LectureStatus.COMPLETED
            )
            db.add(lecture)
            await db.flush()

            db.add(
                LectureSegmentModel(
                    lecture_id=lecture.id,
                    sequence=1,
                    transcript="primeiro trecho",
                    duration_seconds=60.0,
                    offset_seconds=0.0,
                )
            )
            await db.commit()
            lecture_id = lecture.id

        with sync_session() as db:
            found = get_lecture_by_id_sync(db, lecture_id)
            assert found is not None
            assert found.title == "Aula"

            with_segments = get_lecture_with_segments_sync(db, lecture_id)
            assert with_segments is not None
            assert [s.transcript for s in with_segments.segments] == ["primeiro trecho"]

        await async_engine.dispose()
        sync_engine.dispose()
