from __future__ import annotations

import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.sql.elements import ColumnElement

from src.database import SessionLocal
from src.features.files.services.bucket_service import get_bucket_service
from src.features.subjects.ai.chunking import TARGET_CHARS, Chunk, chunk_sections
from src.features.subjects.ai.heading_detection import split_into_sections
from src.features.subjects.ai.text_extraction import extract_elements
from src.features.subjects.models import SubjectDocumentModel

SAMPLE_SIZE = 10
PRICE_PER_MILLION_TOKENS = 0.02


def _find(reference: str) -> SubjectDocumentModel:
    with SessionLocal() as db:
        conditions: list[ColumnElement[bool]] = [
            SubjectDocumentModel.title.ilike(f"%{reference}%")
        ]
        try:
            conditions.append(SubjectDocumentModel.id == UUID(reference))
        except ValueError:
            pass
        found = db.execute(
            select(SubjectDocumentModel).where(or_(*conditions)).limit(1)
        ).scalar_one_or_none()

    if found is None:
        raise SystemExit(f"documento nao encontrado: {reference}")
    return found


def _report(document: SubjectDocumentModel, chunks: list[Chunk], sections: int) -> None:
    sizes = [len(chunk.text) for chunk in chunks]
    levels = Counter(chunk.heading_path.count(">") for chunk in chunks)
    figures = [figure for chunk in chunks for figure in chunk.figures]
    tokens = sum(sizes) // 4

    print(f"\n{document.title}  ({document.page_count or '?'} paginas)")
    print("=" * 72)
    print(f"  secoes                {sections:,}")
    print(f"  chunks                {len(chunks):,}")
    print(f"  tamanho               mediana {int(statistics.median(sizes)):,} | "
          f"min {min(sizes)} | max {max(sizes):,}")
    print(f"  acima do alvo         {sum(1 for size in sizes if size > TARGET_CHARS)} "
          f"({100 * sum(1 for size in sizes if size > TARGET_CHARS) // len(chunks)}%)")
    print(f"  niveis no heading     {dict(sorted(levels.items()))}")
    print(f"  so o nome do doc      {levels.get(0, 0)}")
    print(f"  figuras vinculadas    {len(figures)} em "
          f"{sum(1 for chunk in chunks if chunk.figures)} chunks")
    print(f"  legenda junto         {_captions_together(chunks)}/{len(figures)}")
    sem_ponto = _unfinished(chunks)
    print(f"  sem pontuacao no fim  {sem_ponto} ({100 * sem_ponto // len(chunks)}%)"
          " - inclui fim de secao")
    print(f"  tokens estimados      {tokens:,}")
    print(f"  custo do embedding    ${tokens / 1e6 * PRICE_PER_MILLION_TOKENS:.4f}")

    print(f"\n  amostra de {SAMPLE_SIZE} chunks")
    print("  " + "-" * 70)
    step = max(1, len(chunks) // SAMPLE_SIZE)
    for chunk in chunks[::step][:SAMPLE_SIZE]:
        marca = f" [{len(chunk.figures)} fig]" if chunk.figures else ""
        print(f"  p.{chunk.page_start}-{chunk.page_end} {len(chunk.text):>5}ch{marca}")
        print(f"     {chunk.heading_path[:66]}")
        print(f"     {chunk.text[:66]!r}")


def _unfinished(chunks: list[Chunk]) -> int:
    return sum(1 for chunk in chunks if chunk.text and chunk.text[-1] not in ".!?:;")


def _captions_together(chunks: list[Chunk]) -> int:
    total = 0
    for chunk in chunks:
        normalised = " ".join(chunk.text.split())
        for figure in chunk.figures:
            label = " ".join(figure.caption.split())[:20]
            if label in normalised:
                total += 1
    return total


def main(reference: str) -> None:
    document = _find(reference)
    bucket = get_bucket_service()

    with tempfile.TemporaryDirectory(prefix="inspect-") as tmp:
        source_path = Path(tmp) / document.original_name
        bucket.download_to(document.object_key, source_path)
        elements = extract_elements(source_path)

    sections = split_into_sections(elements, document.title)
    chunks = chunk_sections(sections)
    if not chunks:
        raise SystemExit("nenhum chunk foi produzido")

    _report(document, chunks, len(sections))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("uso: python -m src.features.subjects.inspect_index <id|titulo>")
    main(sys.argv[1])
