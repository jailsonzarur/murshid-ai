from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.features.lectures import tasks
from src.features.lectures.models import LectureModel, LectureStatus
from src.features.lectures.repository import get_lecture_with_segments


@pytest_asyncio.fixture
async def lecture(db_session: AsyncSession, test_user: dict) -> LectureModel:
    model = LectureModel(
        user_id=test_user["id"],
        title="Aula importada",
        status=LectureStatus.PROCESSING,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest.fixture
def use_test_session(test_engine, monkeypatch):
    monkeypatch.setattr(
        tasks,
        "AsyncSessionLocal",
        async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False),
    )


@pytest.fixture
def summary_calls(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        tasks.generate_lecture_summary_task,
        "delay",
        lambda lecture_id: calls.append(lecture_id),
    )
    return calls


def _result(transcript: str, duration: float) -> dict:
    return {"transcript": transcript, "duration": duration}


async def _reload(db_session: AsyncSession, lecture_id):
    db_session.expire_all()
    return await get_lecture_with_segments(db_session, lecture_id)


class TestFinalizeImport:
    async def test_creates_segments_in_order_with_cumulative_offsets(
        self, lecture, use_test_session, summary_calls, db_session
    ):
        results = [
            _result("primeiro", 10.0),
            _result("segundo", 20.0),
            _result("terceiro", 30.0),
        ]

        await tasks._finalize_import_lecture(results, lecture.id)

        refreshed = await _reload(db_session, lecture.id)
        assert refreshed is not None
        assert refreshed.status == LectureStatus.COMPLETED
        assert refreshed.duration_seconds == 60.0

        segments = sorted(refreshed.segments, key=lambda item: item.sequence)
        assert [segment.transcript for segment in segments] == ["primeiro", "segundo", "terceiro"]
        assert [segment.sequence for segment in segments] == [1, 2, 3]
        assert [segment.offset_seconds for segment in segments] == [0.0, 10.0, 30.0]
        assert summary_calls == [str(lecture.id)]

    async def test_marks_failed_when_any_file_gave_up(
        self, lecture, use_test_session, summary_calls, db_session
    ):
        await tasks._finalize_import_lecture([_result("ok", 10.0), None], lecture.id)

        refreshed = await _reload(db_session, lecture.id)
        assert refreshed is not None
        assert refreshed.status == LectureStatus.FAILED
        assert refreshed.segments == []
        assert summary_calls == []

    async def test_redelivery_does_not_duplicate_segments(
        self, lecture, use_test_session, summary_calls, db_session
    ):
        results = [_result("unico", 15.0)]

        await tasks._finalize_import_lecture(results, lecture.id)
        await tasks._finalize_import_lecture(results, lecture.id)

        refreshed = await _reload(db_session, lecture.id)
        assert refreshed is not None
        assert len(refreshed.segments) == 1
        assert refreshed.duration_seconds == 15.0
        assert summary_calls == [str(lecture.id)]

    async def test_missing_lecture_is_a_no_op(self, use_test_session, summary_calls):
        await tasks._finalize_import_lecture([_result("x", 1.0)], uuid4())
        assert summary_calls == []


class TestTranscribeImportFile:
    def test_success_returns_transcript_and_deletes_the_object(self, monkeypatch):
        deleted: list[str] = []
        monkeypatch.setattr(tasks, "_delete_object", deleted.append)

        def transcribe(coro):
            coro.close()
            return "texto transcrito"

        monkeypatch.setattr(tasks, "run_async", transcribe)

        result = tasks.transcribe_import_file_task.run(
            "lecture-1", {"object_key": "lectures/x/02.webm", "duration": 7.5}
        )

        assert result == {"transcript": "texto transcrito", "duration": 7.5}
        assert deleted == ["lectures/x/02.webm"]

    def test_failure_keeps_the_object_for_the_retry(self, monkeypatch):
        deleted: list[str] = []
        monkeypatch.setattr(tasks, "_delete_object", deleted.append)

        def explode(coro):
            coro.close()
            raise TimeoutError("openai timed out")

        monkeypatch.setattr(tasks, "run_async", explode)

        with pytest.raises(Exception):
            tasks.transcribe_import_file_task.run(
                "lecture-1", {"object_key": "lectures/x/03.webm", "duration": 5.0}
            )

        assert deleted == []

    def test_gives_up_after_the_last_retry(self, monkeypatch):
        deleted: list[str] = []
        monkeypatch.setattr(tasks, "_delete_object", deleted.append)

        def explode(coro):
            coro.close()
            raise TimeoutError("openai timed out")

        monkeypatch.setattr(tasks, "run_async", explode)

        task = tasks.transcribe_import_file_task
        monkeypatch.setattr(type(task.request), "retries", tasks.MAX_RETRIES, raising=False)

        result = task.run("lecture-1", {"object_key": "lectures/x/04.webm", "duration": 9.0})

        assert result is None
        assert deleted == ["lectures/x/04.webm"]


class TestDispatch:
    def test_builds_one_header_task_per_file(self, monkeypatch):
        captured = {}

        class FakeChord:
            def __init__(self, header):
                captured["header"] = list(header)

            def __call__(self, callback):
                captured["callback"] = callback

        monkeypatch.setattr(tasks, "chord", FakeChord)

        lecture_id = uuid4()
        items = [
            {"object_key": "a.webm", "duration": 1.0},
            {"object_key": "b.webm", "duration": 2.0},
            {"object_key": "c.webm", "duration": 3.0},
        ]
        tasks.dispatch_import_lecture(lecture_id, items)

        header = captured["header"]
        assert len(header) == 3
        assert [signature.args[1]["object_key"] for signature in header] == ["a.webm", "b.webm", "c.webm"]
        assert captured["callback"].args == (str(lecture_id),)
