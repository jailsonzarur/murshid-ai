from src.features.lectures.ai import audio_chunking
from src.features.lectures.ai.audio_chunking import prepare_audio_for_whisper


async def test_small_file_is_sent_as_a_single_chunk(tmp_path):
    src = tmp_path / "aula.mp3"
    src.write_bytes(b"audio")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    assert await prepare_audio_for_whisper(src, out_dir) == [src]


async def test_transcode_reads_the_original_file_from_disk(tmp_path, monkeypatch):
    src = tmp_path / "aula.mp3"
    src.write_bytes(b"audio")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    seen = {}

    def fake_transcode(source, destination):
        seen["source"] = source
        destination.write_bytes(b"opus")

    def fake_split(source, out, chunk_seconds, prefix):
        chunk = out / f"{prefix}_000.ogg"
        chunk.write_bytes(b"c" * (audio_chunking.MIN_CHUNK_BYTES + 1))
        return [chunk]

    monkeypatch.setattr(audio_chunking, "_transcode_to_opus", fake_transcode)
    monkeypatch.setattr(audio_chunking, "_split_by_time", fake_split)

    chunks = await prepare_audio_for_whisper(
        src, out_dir, duration_hint=audio_chunking.CHUNK_TARGET_SECONDS + 1
    )

    assert seen["source"] == src
    assert [chunk.name for chunk in chunks] == ["aula_000.ogg"]
