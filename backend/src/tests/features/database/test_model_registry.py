"""Regressão: o worker do Celery não chamava init_db(), então users nunca
entrava no metadata e todo flush de aula estourava NoReferencedTableError.
Só quebrou quando a remoção do módulo de provas levou junto o import acidental
que segurava isso."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def it_resolves_every_foreign_key_importing_only_one_model_module():
    # subprocesso porque a suíte já importa tudo; o cenário real é um processo
    # que só toca um módulo de model, como o worker faz
    script = """
import sys
from src.database import Base
from src.features.lectures.models import LectureModel  # noqa: F401

falhas = []
for table in Base.metadata.tables.values():
    for fk in table.foreign_keys:
        try:
            fk.column
        except Exception:
            falhas.append(f"{table.name}.{fk.parent.name} -> {fk._colspec}")

if falhas:
    sys.stdout.write("FK sem tabela alvo: " + ", ".join(falhas))
    sys.exit(1)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def it_registers_every_model_table():
    from src.database import Base

    expected = {"users", "lectures", "lecture_segments", "subjects", "subject_documents"}
    assert expected <= set(Base.metadata.tables)
