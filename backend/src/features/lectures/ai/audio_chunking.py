from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

WHISPER_MAX_BYTES = 24 * 1024 * 1024
CHUNK_TARGET_BYTES = 20 * 1024 * 1024


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
    pattern = out_dir / f"{prefix}_%03d.opus"
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
    return sorted(out_dir.glob(f"{prefix}_*.opus"))


def _prepare_sync(audio_bytes: bytes, filename: str) -> list[tuple[bytes, str]]:
    if len(audio_bytes) <= WHISPER_MAX_BYTES:
        return [(audio_bytes, filename)]

    base = os.path.splitext(os.path.basename(filename))[0] or "audio"

    with tempfile.TemporaryDirectory(prefix="whisper-chunk-") as tmp:
        tmp_dir = Path(tmp)
        suffix = os.path.splitext(filename)[1] or ".bin"
        src_path = tmp_dir / f"input{suffix}"
        src_path.write_bytes(audio_bytes)

        opus_path = tmp_dir / "compressed.opus"
        try:
            _transcode_to_opus(src_path, opus_path)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="replace")[-500:] if exc.stderr else ""
            raise RuntimeError(f"ffmpeg transcode failed: {stderr}") from exc

        opus_bytes = opus_path.read_bytes()
        if len(opus_bytes) <= WHISPER_MAX_BYTES:
            return [(opus_bytes, f"{base}.opus")]

        try:
            duration = _probe_duration_seconds(opus_path)
        except (subprocess.CalledProcessError, ValueError) as exc:
            raise RuntimeError(f"ffprobe failed to read duration of compressed audio: {exc}") from exc

        if duration <= 0:
            raise RuntimeError("compressed audio has non-positive duration")

        chunk_seconds = duration * CHUNK_TARGET_BYTES / len(opus_bytes)
        chunk_seconds = max(30.0, chunk_seconds)

        try:
            chunk_paths = _split_by_time(opus_path, tmp_dir, chunk_seconds, base)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="replace")[-500:] if exc.stderr else ""
            raise RuntimeError(f"ffmpeg split failed: {stderr}") from exc

        if not chunk_paths:
            raise RuntimeError("ffmpeg produced no chunks")

        chunks: list[tuple[bytes, str]] = []
        for path in chunk_paths:
            data = path.read_bytes()
            if len(data) > WHISPER_MAX_BYTES:
                logger.warning(
                    "audio chunk %s is %d bytes, above Whisper limit; Whisper will likely reject it",
                    path.name,
                    len(data),
                )
            chunks.append((data, path.name))
        return chunks


async def prepare_audio_for_whisper(audio_bytes: bytes, filename: str) -> list[tuple[bytes, str]]:
    """Return chunks ready for the Whisper API (each ≤ 25 MB).

    Small files are passed through. Larger files are re-encoded to opus mono
    24 kbps; if still too large, they are split into time-based chunks.
    """
    return await asyncio.to_thread(_prepare_sync, audio_bytes, filename)
