from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

WHISPER_MAX_BYTES = 24 * 1024 * 1024
CHUNK_TARGET_BYTES = 20 * 1024 * 1024
# os modelos gpt-*-transcribe têm teto de 2000 tokens de saída, que o whisper
# não tinha; 10 min de fala densa em português encostam nesse limite e o texto
# sai truncado sem erro. 5 min deixa o dobro de folga.
CHUNK_TARGET_SECONDS = 300
MIN_CHUNK_BYTES = 4 * 1024


def _run(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(cmd, check=True, capture_output=True)


def _probe_duration_seconds(path: Path) -> float:
    proc = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    return float(proc.stdout.decode().strip())


def _transcode_to_opus(src: Path, dst: Path) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "libopus",
            "-b:a",
            "24k",
            str(dst),
        ]
    )


def _split_by_time(src: Path, out_dir: Path, chunk_seconds: float, prefix: str) -> list[Path]:
    pattern = out_dir / f"{prefix}_%03d.ogg"
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-f",
            "segment",
            "-segment_time",
            f"{chunk_seconds:.3f}",
            "-reset_timestamps",
            "1",
            "-c",
            "copy",
            str(pattern),
        ]
    )
    return sorted(out_dir.glob(f"{prefix}_*.ogg"))


def _prepare_sync(src_path: Path, out_dir: Path, duration_hint: float | None = None) -> list[Path]:
    longo = duration_hint is not None and duration_hint > CHUNK_TARGET_SECONDS
    if src_path.stat().st_size <= WHISPER_MAX_BYTES and not longo:
        return [src_path]

    base = src_path.stem or "audio"
    opus_path = out_dir / f"{base}.ogg"
    try:
        _transcode_to_opus(src_path, opus_path)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace")[-500:] if exc.stderr else ""
        raise RuntimeError(f"ffmpeg transcode failed: {stderr}") from exc

    opus_size = opus_path.stat().st_size
    if opus_size <= WHISPER_MAX_BYTES and not longo:
        return [opus_path]

    if duration_hint is not None:
        duration = duration_hint
    else:
        try:
            duration = _probe_duration_seconds(opus_path)
        except (subprocess.CalledProcessError, ValueError) as exc:
            raise RuntimeError(f"ffprobe failed to read duration of compressed audio: {exc}") from exc

    if duration <= 0:
        raise RuntimeError("compressed audio has non-positive duration")

    chunk_seconds = duration * CHUNK_TARGET_BYTES / opus_size
    chunk_seconds = min(chunk_seconds, CHUNK_TARGET_SECONDS)
    chunk_seconds = max(30.0, chunk_seconds)

    try:
        chunk_paths = _split_by_time(opus_path, out_dir, chunk_seconds, base)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace")[-500:] if exc.stderr else ""
        raise RuntimeError(f"ffmpeg split failed: {stderr}") from exc

    if not chunk_paths:
        raise RuntimeError("ffmpeg produced no chunks")

    chunks: list[Path] = []
    for path in chunk_paths:
        size = path.stat().st_size
        if size < MIN_CHUNK_BYTES:
            logger.info("discarding empty audio chunk %s (%d bytes)", path.name, size)
            continue
        if size > WHISPER_MAX_BYTES:
            logger.warning(
                "audio chunk %s is %d bytes, above Whisper limit; Whisper will likely reject it",
                path.name,
                size,
            )
        chunks.append(path)

    if not chunks:
        raise RuntimeError("no usable audio chunks after split")

    return chunks


async def prepare_audio_for_whisper(
    src_path: Path, out_dir: Path, duration_hint: float | None = None
) -> list[Path]:
    return await asyncio.to_thread(_prepare_sync, src_path, out_dir, duration_hint)
