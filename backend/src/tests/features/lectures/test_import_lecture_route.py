from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from starlette.datastructures import UploadFile

from src.features.lectures.models import LectureStatus
from src.features.lectures.routes import import_lecture as route
from src.features.lectures.schemas.lecture_schemas import LectureSummarySchema

AUDIO_MIME = "audio/mpeg"


def _summary() -> LectureSummarySchema:
    now = datetime.now(UTC)
    return LectureSummarySchema(
        id=uuid4(),
        user_id=uuid4(),
        title="Aula importada",
        status=LectureStatus.PROCESSING,
        duration_seconds=0.0,
        nodes_count=0,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def import_calls(monkeypatch):
    """Isola a rota do MinIO e do Celery, guardando o que chegaria no service."""
    calls: list[dict] = []

    async def fake_start_import_lecture(db, **kwargs):
        calls.append(kwargs)
        return _summary()

    monkeypatch.setattr(route, "start_import_lecture", fake_start_import_lecture)
    return calls


@pytest.fixture
def forbid_read(monkeypatch):
    """Faz qualquer leitura de conteúdo estourar.

    A validação da Fase 1 tem que rejeitar o request olhando só `UploadFile.size`;
    se algum caminho de erro ainda chamar `.read()`, o teste quebra.
    """

    async def explode(self, size: int = -1) -> bytes:
        raise AssertionError("o conteúdo do upload foi lido antes de passar na validação")

    monkeypatch.setattr(UploadFile, "read", explode)


def _files(*sizes: int, mime: str = AUDIO_MIME) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [
        ("files", (f"aula_{index + 1}.mp3", b"x" * size, mime))
        for index, size in enumerate(sizes)
    ]


async def _post(client: AsyncClient, headers: dict, files, durations) -> object:
    return await client.post(
        "/lectures/import",
        headers=headers,
        files=files,
        data={"title": "Aula", "durations": json.dumps(durations)},
    )


def _error(response) -> str:
    return response.json()["errors"][0]


class TestImportLectureValidation:
    async def test_accepts_a_valid_upload(self, client: AsyncClient, guest_headers: dict, import_calls):
        response = await _post(client, guest_headers, _files(1024), [12.5])

        assert response.status_code == 201
        assert len(import_calls) == 1
        items = import_calls[0]["audio_items"]
        assert [item["duration"] for item in items] == [12.5]
        assert items[0]["content"] == b"x" * 1024

    async def test_rejects_a_file_above_the_individual_limit_without_reading_it(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read, monkeypatch
    ):
        monkeypatch.setattr(route, "MAX_FILE_BYTES", 1024)

        response = await _post(client, guest_headers, _files(2048), [10.0])

        assert response.status_code == 400
        assert "excede o limite" in _error(response)
        assert import_calls == []

    async def test_rejects_when_the_files_together_exceed_the_aggregate_limit(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read, monkeypatch
    ):
        monkeypatch.setattr(route, "MAX_TOTAL_BYTES", 3000)

        response = await _post(client, guest_headers, _files(1024, 1024, 1024), [10.0, 10.0, 10.0])

        assert response.status_code == 400
        assert "somam mais de" in _error(response)
        assert import_calls == []

    async def test_rejects_an_empty_file_without_reading_it(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read
    ):
        response = await _post(client, guest_headers, _files(0), [10.0])

        assert response.status_code == 400
        assert "está vazio" in _error(response)
        assert import_calls == []

    async def test_rejects_an_unsupported_mime_type(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read
    ):
        response = await _post(client, guest_headers, _files(1024, mime="application/pdf"), [10.0])

        assert response.status_code == 400
        assert "Formato não suportado" in _error(response)
        assert import_calls == []

    async def test_rejects_an_invalid_duration_before_reading_any_file(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read
    ):
        response = await _post(client, guest_headers, _files(1024, 1024), [10.0, 0])

        assert response.status_code == 400
        assert "Duração inválida" in _error(response)
        assert import_calls == []

    async def test_a_late_invalid_file_does_not_cost_reading_the_earlier_ones(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read
    ):
        files = _files(1024) + _files(1024, mime="application/pdf")

        response = await _post(client, guest_headers, files, [10.0, 10.0])

        assert response.status_code == 400
        assert import_calls == []

    async def test_rejects_more_files_than_the_limit(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read, monkeypatch
    ):
        monkeypatch.setattr(route, "MAX_FILES", 2)

        response = await _post(client, guest_headers, _files(64, 64, 64), [1.0, 1.0, 1.0])

        assert response.status_code == 400
        assert "Máximo de 2 arquivos" in _error(response)
        assert import_calls == []

    async def test_rejects_durations_that_do_not_match_the_files(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read
    ):
        response = await _post(client, guest_headers, _files(64, 64), [1.0])

        assert response.status_code == 400
        assert "uma duração" in _error(response)
        assert import_calls == []

    async def test_rejects_malformed_durations_json(
        self, client: AsyncClient, guest_headers: dict, import_calls, forbid_read
    ):
        response = await client.post(
            "/lectures/import",
            headers=guest_headers,
            files=_files(64),
            data={"title": "Aula", "durations": "nao-e-json"},
        )

        assert response.status_code == 400
        assert "JSON válido" in _error(response)
        assert import_calls == []
