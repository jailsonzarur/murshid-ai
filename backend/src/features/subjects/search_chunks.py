from __future__ import annotations

import sys
from uuid import UUID

from sqlalchemy import select

from src.database import SessionLocal
from src.features.subjects.ai.embedding import embed_texts
from src.features.subjects.models import SubjectDocumentModel, SubjectModel
from src.features.subjects.repository import search_subject_chunks_sync

DEFAULT_LIMIT = 5
SNIPPET = 220


def main(subject_name: str, query: str, limit: int = DEFAULT_LIMIT) -> None:
    with SessionLocal() as db:
        subject = db.execute(
            select(SubjectModel).where(SubjectModel.name == subject_name).limit(1)
        ).scalar_one_or_none()
        if subject is None:
            subject = db.execute(
                select(SubjectModel)
                .where(SubjectModel.name.ilike(f"%{subject_name}%"))
                .order_by(SubjectModel.name)
                .limit(1)
            ).scalar_one_or_none()
        if subject is None:
            raise SystemExit(f"materia nao encontrada: {subject_name}")

        vector = embed_texts([query])[0]
        found = search_subject_chunks_sync(db, subject.id, vector, limit=limit)

        titles: dict[UUID, str] = {
            row.id: row.title
            for row in db.execute(
                select(SubjectDocumentModel.id, SubjectDocumentModel.title).where(
                    SubjectDocumentModel.subject_id == subject.id
                )
            ).all()
        }

        print(f'\nmateria: {subject.name}')
        print(f'consulta: "{query}"')
        print("=" * 78)
        if not found:
            print("  nenhum chunk indexado nesta materia")
            return

        for position, (chunk, distance) in enumerate(found, start=1):
            documento = titles.get(chunk.document_id, "?")
            print(f"\n[{position}] distancia {distance:.4f}  |  {documento}  p.{chunk.page_start}")
            print(f"    {chunk.heading_path[:74]}")
            print(f"    {' '.join(chunk.text.split())[:SNIPPET]}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(
            'uso: python -m src.features.subjects.search_chunks "<materia>" "<consulta>" [limite]'
        )
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_LIMIT)
