from __future__ import annotations

import subprocess

import pytest

from src.features.subjects.ai import pdf_compression


class _Resultado:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.stderr = b""


@pytest.fixture
def original(tmp_path):
    caminho = tmp_path / "livro.pdf"
    caminho.write_bytes(b"x" * 1000)
    return caminho


class TestCompressPdf:
    def test_replaces_the_file_when_the_gain_is_real(self, monkeypatch, tmp_path, original):
        alvo = tmp_path / "menor.pdf"

        def fake_run(args, **kwargs):
            alvo.write_bytes(b"x" * 200)
            return _Resultado(0)

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert pdf_compression.compress_pdf(original, alvo) is True
        assert alvo.exists()

    def test_discards_the_result_when_the_gain_is_marginal(self, monkeypatch, tmp_path, original):
        alvo = tmp_path / "menor.pdf"

        def fake_run(args, **kwargs):
            alvo.write_bytes(b"x" * 950)
            return _Resultado(0)

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert pdf_compression.compress_pdf(original, alvo) is False
        assert not alvo.exists()

    def test_a_crashing_subprocess_is_not_fatal(self, monkeypatch, tmp_path, original):
        alvo = tmp_path / "menor.pdf"
        monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: _Resultado(-11))

        assert pdf_compression.compress_pdf(original, alvo) is False
        assert not alvo.exists()

    def test_retries_until_one_attempt_survives(self, monkeypatch, tmp_path, original):
        alvo = tmp_path / "menor.pdf"
        chamadas = {"n": 0}

        def fake_run(args, **kwargs):
            chamadas["n"] += 1
            if chamadas["n"] < 3:
                return _Resultado(-11)
            alvo.write_bytes(b"x" * 150)
            return _Resultado(0)

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert pdf_compression.compress_pdf(original, alvo) is True
        assert chamadas["n"] == 3

    def test_gives_up_after_the_configured_attempts(self, monkeypatch, tmp_path, original):
        alvo = tmp_path / "menor.pdf"
        chamadas = {"n": 0}

        def fake_run(args, **kwargs):
            chamadas["n"] += 1
            return _Resultado(-11)

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert pdf_compression.compress_pdf(original, alvo) is False
        assert chamadas["n"] == pdf_compression.ATTEMPTS
