from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.subjects.models import (
    EMBEDDING_DIMENSIONS,
    SubjectDocumentChunkModel,
    SubjectDocumentImageModel,
    SubjectDocumentIndexStatus,
    SubjectDocumentModel,
    SubjectModel,
)


@pytest_asyncio.fixture
async def document(db_session: AsyncSession, test_user: dict) -> SubjectDocumentModel:
    subject = SubjectModel(user_id=test_user["id"], name="Microbiologia")
    db_session.add(subject)
    await db_session.flush()

    model = SubjectDocumentModel(
        subject_id=subject.id,
        title="Murray",
        original_name="murray.pdf",
        object_key="subjects/x/documents/murray.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
    )
    db_session.add(model)
    await db_session.commit()
    return model


def _embedding(value: float = 0.0) -> list[float]:
    return [value] * EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
class TestIndexStatus:
    async def test_a_new_document_starts_unindexed(self, document: SubjectDocumentModel):
        assert document.index_status == SubjectDocumentIndexStatus.NONE
        assert document.chunk_count is None


@pytest.mark.asyncio
class TestChunks:
    async def test_a_chunk_keeps_its_heading_and_pages(
        self, db_session: AsyncSession, document: SubjectDocumentModel
    ):
        db_session.add(
            SubjectDocumentChunkModel(
                document_id=document.id,
                subject_id=document.subject_id,
                sequence=1,
                text="Os derivativos apresentam liquidez concentrada.",
                heading_path="Murray > Bactérias > Parede Celular",
                page_start=287,
                page_end=288,
                embedding=_embedding(),
            )
        )
        await db_session.commit()

        found = (await db_session.execute(select(SubjectDocumentChunkModel))).scalar_one()
        assert found.heading_path == "Murray > Bactérias > Parede Celular"
        assert (found.page_start, found.page_end) == (287, 288)
        assert len(found.embedding) == EMBEDDING_DIMENSIONS

    async def test_the_sequence_is_unique_per_document(
        self, db_session: AsyncSession, document: SubjectDocumentModel
    ):
        for _ in range(2):
            db_session.add(
                SubjectDocumentChunkModel(
                    document_id=document.id,
                    subject_id=document.subject_id,
                    sequence=1,
                    text="t",
                    heading_path="h",
                    embedding=_embedding(),
                )
            )

        with pytest.raises(Exception):
            await db_session.commit()


@pytest.mark.asyncio
class TestImages:
    async def test_a_chunk_can_carry_more_than_one_image(
        self, db_session: AsyncSession, document: SubjectDocumentModel
    ):
        chunk = SubjectDocumentChunkModel(
            document_id=document.id,
            subject_id=document.subject_id,
            sequence=1,
            text="t",
            heading_path="h",
            embedding=_embedding(),
        )
        db_session.add(chunk)
        await db_session.flush()

        for page in (12, 13):
            db_session.add(
                SubjectDocumentImageModel(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    page=page,
                    bbox={"x0": 10, "y0": 20, "x1": 300, "y1": 400},
                    caption=f"FIGURA {page}-1 Estrutura da parede celular",
                )
            )
        await db_session.commit()

        total = await db_session.scalar(
            select(func.count()).select_from(SubjectDocumentImageModel)
        )
        assert total == 2

    async def test_an_image_may_have_no_chunk_yet(
        self, db_session: AsyncSession, document: SubjectDocumentModel
    ):
        db_session.add(
            SubjectDocumentImageModel(
                document_id=document.id,
                page=1,
                bbox={"x0": 0, "y0": 0, "x1": 1, "y1": 1},
            )
        )
        await db_session.commit()

        found = (await db_session.execute(select(SubjectDocumentImageModel))).scalar_one()
        assert found.chunk_id is None
        assert found.caption is None
