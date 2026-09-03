from pathlib import Path

from src.features.lectures.ai import transcription


async def test_chunks_are_read_from_disk_and_joined_in_order(tmp_path, monkeypatch):
    chunks = []
    for index, text in enumerate(["primeiro", "segundo", "terceiro"]):
        chunk = tmp_path / f"aula_{index:03d}.ogg"
        chunk.write_bytes(text.encode())
        chunks.append(chunk)

    async def fake_prepare(src_path, out_dir, duration_hint=None):
        return chunks

    async def fake_transcribe(audio_bytes, filename):
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

    async def fake_transcribe(audio_bytes, filename):
        seen["filename"] = filename
        return audio_bytes.decode()

    monkeypatch.setattr(transcription, "prepare_audio_for_whisper", fake_prepare)
    monkeypatch.setattr(transcription, "transcribe_audio_chunk", fake_transcribe)

    assert await transcription.transcribe_audio_file(Path(chunk)) == "conteudo"
    assert seen["filename"] == "aula.mp3"
