from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.features.subjects.ai.chunking import Chunk
from src.features.subjects.ai.text_extraction import Figure
from src.features.subjects.models import (
    EMBEDDING_DIMENSIONS,
    SubjectDocumentChunkModel,
    SubjectDocumentImageModel,
    SubjectDocumentIndexStatus,
    SubjectDocumentModel,
    SubjectModel,
)
from src.features.subjects.services import subject_index_service
from src.features.users.models import UserModel


@pytest.fixture
def session_factory(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/index.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(subject_index_service, "SessionLocal", factory)
    return factory


@pytest.fixture
def document(session_factory) -> SubjectDocumentModel:
    with session_factory() as db:
        user = UserModel(name="Dono", email="dono@example.com", password="x")
        db.add(user)
        db.flush()

        subject = SubjectModel(user_id=user.id, name="Microbiologia")
        db.add(subject)
        db.flush()

        model = SubjectDocumentModel(
            subject_id=subject.id,
            title="Murray",
            original_name="murray.pdf",
            object_key="subjects/x/murray.pdf",
            mime_type="application/pdf",
            size_bytes=10,
        )
        db.add(model)
        db.commit()
        return model


def _chunk(sequence: int, figures: list[Figure] | None = None) -> Chunk:
    return Chunk(
        text=f"trecho {sequence}",
        heading_path="Murray > Bactérias",
        page_start=sequence,
        page_end=sequence,
        figures=figures or [],
    )


def _fake_pipeline(monkeypatch, chunks: list[Chunk]) -> dict:
    visto: dict = {}

    def fake_build(object_key, original_name, title):
        visto["title"] = title
        return chunks

    def fake_embed(texts):
        visto["texts"] = texts
        return [[0.1] * EMBEDDING_DIMENSIONS for _ in texts]

    monkeypatch.setattr(subject_index_service, "_build_chunks", fake_build)
    monkeypatch.setattr(subject_index_service, "embed_texts", fake_embed)
    return visto


class TestClaim:
    def test_the_first_claim_wins(self, session_factory, document):
        assert subject_index_service.claim_document_for_indexing(document.id) is True

    def test_a_second_claim_is_refused(self, session_factory, document):
        subject_index_service.claim_document_for_indexing(document.id)

        assert subject_index_service.claim_document_for_indexing(document.id) is False

    def test_a_failed_document_can_be_claimed_again(self, session_factory, document):
        subject_index_service.claim_document_for_indexing(document.id)
        subject_index_service.set_failed(document.id)

        assert subject_index_service.claim_document_for_indexing(document.id) is True


class TestIndexing:
    def test_chunks_are_persisted_with_their_heading(
        self, session_factory, document, monkeypatch
    ):
        _fake_pipeline(monkeypatch, [_chunk(1), _chunk(2)])

        subject_index_service.index_document(document.id)

        with session_factory() as db:
            rows = db.execute(select(SubjectDocumentChunkModel)).scalars().all()
            assert [row.sequence for row in rows] == [1, 2]
            assert rows[0].heading_path == "Murray > Bactérias"
            assert len(rows[0].embedding) == EMBEDDING_DIMENSIONS

    def test_the_heading_prefixes_the_embedded_text_only(
        self, session_factory, document, monkeypatch
    ):
        visto = _fake_pipeline(monkeypatch, [_chunk(1)])

        subject_index_service.index_document(document.id)

        assert visto["texts"] == ["Murray > Bactérias\ntrecho 1"]
        with session_factory() as db:
            row = db.execute(select(SubjectDocumentChunkModel)).scalar_one()
            assert row.text == "trecho 1"

    def test_the_document_title_names_the_first_level(
        self, session_factory, document, monkeypatch
    ):
        visto = _fake_pipeline(monkeypatch, [_chunk(1)])

        subject_index_service.index_document(document.id)

        assert visto["title"] == "Murray"

    def test_figures_are_linked_to_their_chunk(self, session_factory, document, monkeypatch):
        figura = Figure(page=12, bbox=(1.0, 2.0, 3.0, 4.0), caption="FIGURA 1-1 Parede")
        _fake_pipeline(monkeypatch, [_chunk(1, [figura])])

        subject_index_service.index_document(document.id)

        with session_factory() as db:
            chunk = db.execute(select(SubjectDocumentChunkModel)).scalar_one()
            image = db.execute(select(SubjectDocumentImageModel)).scalar_one()
            assert image.chunk_id == chunk.id
            assert image.bbox == {"x0": 1.0, "y0": 2.0, "x1": 3.0, "y1": 4.0}
            assert image.caption == "FIGURA 1-1 Parede"

    def test_the_document_is_marked_done_with_its_count(
        self, session_factory, document, monkeypatch
    ):
        _fake_pipeline(monkeypatch, [_chunk(1), _chunk(2), _chunk(3)])

        subject_index_service.index_document(document.id)

        with session_factory() as db:
            found = db.get(SubjectDocumentModel, document.id)
            assert found is not None
            assert found.index_status == SubjectDocumentIndexStatus.DONE
            assert found.chunk_count == 3

    def test_an_empty_document_is_marked_failed(self, session_factory, document, monkeypatch):
        _fake_pipeline(monkeypatch, [])

        subject_index_service.index_document(document.id)

        with session_factory() as db:
            found = db.get(SubjectDocumentModel, document.id)
            assert found is not None
            assert found.index_status == SubjectDocumentIndexStatus.FAILED


class TestReindexing:
    def test_running_twice_does_not_duplicate(self, session_factory, document, monkeypatch):
        _fake_pipeline(monkeypatch, [_chunk(1), _chunk(2)])
        subject_index_service.index_document(document.id)

        subject_index_service.set_failed(document.id)
        subject_index_service.index_document(document.id)

        with session_factory() as db:
            total = db.scalar(select(func.count()).select_from(SubjectDocumentChunkModel))
            assert total == 2

    def test_old_figures_are_cleared_too(self, session_factory, document, monkeypatch):
        figura = Figure(page=1, bbox=(0.0, 0.0, 1.0, 1.0), caption="FIGURA 1-1 Velha")
        _fake_pipeline(monkeypatch, [_chunk(1, [figura])])
        subject_index_service.index_document(document.id)

        subject_index_service.set_failed(document.id)
        _fake_pipeline(monkeypatch, [_chunk(1)])
        subject_index_service.index_document(document.id)

        with session_factory() as db:
            total = db.scalar(select(func.count()).select_from(SubjectDocumentImageModel))
            assert total == 0
