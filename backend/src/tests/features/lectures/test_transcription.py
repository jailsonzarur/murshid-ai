from pathlib import Path

import pytest

from src.features.lectures.ai import transcription


async def test_chunks_are_read_from_disk_and_joined_in_order(tmp_path, monkeypatch):
    chunks = []
    for index, text in enumerate(["primeiro", "segundo", "terceiro"]):
        chunk = tmp_path / f"aula_{index:03d}.ogg"
        chunk.write_bytes(text.encode())
        chunks.append(chunk)

    async def fake_prepare(src_path, out_dir, duration_hint=None):
        return chunks

    def fake_transcribe(audio_bytes, filename):
        return audio_bytes.decode()

    monkeypatch.setattr(transcription, "prepare_audio_for_whisper", fake_prepare)
    monkeypatch.setattr(transcription, "transcribe_audio_chunk", fake_transcribe)

    result = await transcription.transcribe_audio_file(tmp_path / "aula.mp3")

    assert result == "primeiro segundo terceiro"


async def test_a_single_chunk_is_transcribed_directly(tmp_path, monkeypatch):
    chunk = tmp_path / "aula.mp3"
    chunk.write_bytes(b"conteudo")
    seen = {}

    async def fake_prepare(src_path, out_dir, duration_hint=None):
        return [chunk]

    def fake_transcribe(audio_bytes, filename):
        seen["filename"] = filename
        return audio_bytes.decode()

    monkeypatch.setattr(transcription, "prepare_audio_for_whisper", fake_prepare)
    monkeypatch.setattr(transcription, "transcribe_audio_chunk", fake_transcribe)

    assert await transcription.transcribe_audio_file(Path(chunk)) == "conteudo"
    assert seen["filename"] == "aula.mp3"


@pytest.fixture
def sem_dotenv(monkeypatch, tmp_path):
    import decouple

    monkeypatch.setattr(decouple, "config", decouple.AutoConfig(str(tmp_path)))


class TestProviderSwitch:
    def test_openai_is_the_default(self, monkeypatch, sem_dotenv):
        import importlib

        monkeypatch.delenv("TRANSCRIPTION_PROVIDER", raising=False)
        reloaded = importlib.reload(transcription)
        assert reloaded.TRANSCRIPTION_PROVIDER == "openai"
        assert reloaded.TRANSCRIPTION_MODEL == "whisper-1"

    def test_previous_text_conditioning_is_off_by_default(self, monkeypatch, sem_dotenv):
        import importlib

        monkeypatch.delenv("TRANSCRIPTION_CONDITION_ON_PREVIOUS", raising=False)
        reloaded = importlib.reload(transcription)
        assert reloaded.TRANSCRIPTION_CONDITION_ON_PREVIOUS is False

    def test_cloudflare_picks_its_own_default_model(self, monkeypatch):
        import importlib

        monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "cloudflare")
        monkeypatch.delenv("TRANSCRIPTION_MODEL", raising=False)
        reloaded = importlib.reload(transcription)
        assert reloaded.TRANSCRIPTION_PROVIDER == "cloudflare"
        assert reloaded.TRANSCRIPTION_MODEL == "@cf/openai/whisper-large-v3-turbo"
        monkeypatch.delenv("TRANSCRIPTION_PROVIDER")
        importlib.reload(transcription)

    def test_cloudflare_sends_base64_audio(self, monkeypatch):
        import base64
        import importlib

        monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "cloudflare")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "conta")
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "segredo")
        monkeypatch.setenv("TRANSCRIPTION_CONDITION_ON_PREVIOUS", "true")
        reloaded = importlib.reload(transcription)

        sent = {}

        class _Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"success": True, "result": {"text": "olá turma"}}

        def fake_post(url, headers=None, json=None, timeout=None):
            sent["url"] = url
            sent["headers"] = headers
            sent["json"] = json
            return _Response()

        import httpx

        monkeypatch.setattr(httpx, "post", fake_post)

        assert reloaded.transcribe_audio_chunk(b"audio-bruto", "0000.ogg") == "olá turma"
        assert sent["url"].endswith("/conta/ai/run/@cf/openai/whisper-large-v3-turbo")
        assert sent["headers"]["Authorization"] == "Bearer segredo"
        assert base64.b64decode(sent["json"]["audio"]) == b"audio-bruto"
        assert "initial_prompt" not in sent["json"]
        assert sent["json"]["language"] == "pt"
        assert sent["json"]["condition_on_previous_text"] is True

        for key in ("TRANSCRIPTION_PROVIDER", "TRANSCRIPTION_CONDITION_ON_PREVIOUS"):
            monkeypatch.delenv(key)
        importlib.reload(transcription)

    def test_a_cloudflare_failure_raises(self, monkeypatch):
        import importlib

        monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "cloudflare")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "conta")
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "segredo")
        reloaded = importlib.reload(transcription)

        class _Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"success": False, "errors": [{"message": "quota"}]}

        import httpx

        monkeypatch.setattr(httpx, "post", lambda *a, **k: _Response())

        import pytest as _pytest

        with _pytest.raises(RuntimeError, match="cloudflare"):
            reloaded.transcribe_audio_chunk(b"x", "0000.ogg")

        monkeypatch.delenv("TRANSCRIPTION_PROVIDER")
        importlib.reload(transcription)
