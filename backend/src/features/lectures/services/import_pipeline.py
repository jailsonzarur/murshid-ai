from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from src.database import AsyncSessionLocal
from src.features.files.services.bucket_service import get_bucket_service
from src.features.lectures.ai.audio_chunking import (
    prepare_audio_for_whisper,
    probe_duration_seconds,
)
from src.features.lectures.ai.transcription import TRANSCRIPTION_MODEL, transcribe_chunk_path
from src.features.lectures.models import (
    LectureAudioChunkModel,
    LectureAudioStatus,
    LectureSegmentModel,
    LectureStatus,
)
from src.features.lectures.repository import (
    add_segment,
    claim_audio_for_consolidation,
    claim_lecture_finalization,
    get_audio,
    get_audio_chunk,
    get_audio_with_chunks,
    list_audio_ids_for_lecture,
    sum_audio_duration_before,
)

logger = logging.getLogger(__name__)


async def transcribe_chunk(chunk_id: UUID) -> UUID | None:
    async with AsyncSessionLocal() as db:
        chunk = await get_audio_chunk(db, chunk_id)
        if chunk is None:
            logger.warning("transcribe_chunk: chunk %s not found", chunk_id)
            return None
        if chunk.transcript is not None:
            return chunk.audio_id

        audio_id = chunk.audio_id
        object_key = chunk.object_key
        chunk.attempts += 1
        await db.commit()

    try:
        with tempfile.TemporaryDirectory(prefix="whisper-chunk-") as tmp:
            path = Path(tmp) / object_key.rsplit("/", 1)[-1]
            bucket = get_bucket_service()
            await asyncio.to_thread(bucket.download_to, object_key, path)
            transcript = await transcribe_chunk_path(path)
    except Exception as exc:
        await _record_failure(chunk_id, exc)
        raise

    async with AsyncSessionLocal() as db:
        chunk = await get_audio_chunk(db, chunk_id)
        if chunk is None:
            return audio_id
        if chunk.transcript is None:
            chunk.transcript = transcript
            chunk.last_error = None
            await db.commit()

    return audio_id


async def _record_failure(chunk_id: UUID, exc: BaseException) -> None:
    try:
        async with AsyncSessionLocal() as db:
            chunk = await get_audio_chunk(db, chunk_id)
            if chunk is None:
                return
            chunk.last_error = f"{type(exc).__name__}: {exc}"[:2000]
            await db.commit()
    except Exception:
        logger.exception("transcribe_chunk: could not record failure for chunk %s", chunk_id)


async def start_import(lecture_id: UUID) -> list[UUID]:
    async with AsyncSessionLocal() as db:
        return await list_audio_ids_for_lecture(db, lecture_id)


async def lecture_id_of_audio(audio_id: UUID) -> UUID | None:
    async with AsyncSessionLocal() as db:
        audio = await get_audio(db, audio_id)
        return None if audio is None else audio.lecture_id


async def finalize_lecture(lecture_id: UUID) -> LectureStatus | None:
    async with AsyncSessionLocal() as db:
        outcome = await claim_lecture_finalization(db, lecture_id)
        if outcome is None:
            return None
        await db.commit()

    return outcome


async def mark_audio_failed(audio_id: UUID, reason: str) -> None:
    async with AsyncSessionLocal() as db:
        audio = await get_audio(db, audio_id)
        if audio is None or audio.status is LectureAudioStatus.DONE:
            return
        audio.status = LectureAudioStatus.FAILED
        audio.last_error = reason[:2000]
        await db.commit()


async def fail_audio_of_chunk(chunk_id: UUID, reason: str) -> UUID | None:
    async with AsyncSessionLocal() as db:
        chunk = await get_audio_chunk(db, chunk_id)
        if chunk is None:
            return None
        audio_id = chunk.audio_id

    await mark_audio_failed(audio_id, reason)
    return await lecture_id_of_audio(audio_id)


async def chunk_audio(audio_id: UUID) -> list[UUID]:
    async with AsyncSessionLocal() as db:
        audio = await get_audio(db, audio_id)
        if audio is None:
            logger.warning("chunk_audio: audio %s not found", audio_id)
            return []
        if audio.status not in {LectureAudioStatus.PENDING, LectureAudioStatus.CHUNKING}:
            return []

        audio.status = LectureAudioStatus.CHUNKING
        await db.commit()

        lecture_id = audio.lecture_id
        object_key = audio.object_key
        duration_hint = audio.duration_seconds

    bucket = get_bucket_service()
    specs: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="whisper-audio-") as tmp:
        out_dir = Path(tmp)
        src_path = out_dir / object_key.rsplit("/", 1)[-1]
        await asyncio.to_thread(bucket.download_to, object_key, src_path)

        paths = await prepare_audio_for_whisper(src_path, out_dir, duration_hint)

        start = 0.0
        for sequence, path in enumerate(paths):
            seconds = await probe_duration_seconds(path)
            key = f"lectures/{lecture_id}/chunks/{audio_id}/{sequence:04d}{path.suffix}"
            await asyncio.to_thread(_upload_chunk, bucket, path, key)
            specs.append(
                {
                    "audio_id": audio_id,
                    "sequence": sequence,
                    "object_key": key,
                    "start_seconds": start,
                    "duration_seconds": seconds,
                }
            )
            start += seconds

    async with AsyncSessionLocal() as db:
        statement = insert(LectureAudioChunkModel).values(specs)
        await db.execute(
            statement.on_conflict_do_update(
                constraint="uq_lecture_audio_chunks_audio_id_sequence",
                set_={
                    "object_key": statement.excluded.object_key,
                    "start_seconds": statement.excluded.start_seconds,
                    "duration_seconds": statement.excluded.duration_seconds,
                },
            )
        )
        audio = await get_audio_with_chunks(db, audio_id)
        if audio is None:
            return []
        audio.status = LectureAudioStatus.TRANSCRIBING
        chunk_ids = [chunk.id for chunk in audio.chunks]
        await db.commit()

    return chunk_ids


def _upload_chunk(bucket, path: Path, key: str) -> None:
    with path.open("rb") as stream:
        bucket.upload_stream(
            stream,
            path.name,
            length=path.stat().st_size,
            content_type="audio/ogg",
            key=key,
        )


async def consolidate_audio(audio_id: UUID) -> UUID | None:
    async with AsyncSessionLocal() as db:
        if not await claim_audio_for_consolidation(db, audio_id):
            return None

        audio = await get_audio_with_chunks(db, audio_id)
        if audio is None:
            return None

        chunks = list(audio.chunks)
        transcript = " ".join(
            chunk.transcript.strip() for chunk in chunks if chunk.transcript and chunk.transcript.strip()
        )
        offset = await sum_audio_duration_before(db, audio.lecture_id, audio.sequence)

        await add_segment(
            db,
            LectureSegmentModel(
                lecture_id=audio.lecture_id,
                sequence=audio.sequence,
                transcript=transcript,
                duration_seconds=audio.duration_seconds,
                offset_seconds=offset,
            ),
        )

        audio.transcribed_seconds = sum(chunk.duration_seconds for chunk in chunks)
        audio.model = TRANSCRIPTION_MODEL
        audio.last_error = None
        keys = [chunk.object_key for chunk in chunks] + [audio.object_key]
        lecture_id = audio.lecture_id

        for chunk in chunks:
            await db.delete(chunk)

        await db.commit()

    _delete_objects(keys)

    return lecture_id


def _delete_objects(keys: list[str]) -> None:
    if not keys:
        return
    try:
        get_bucket_service().delete_many(keys)
    except Exception:
        logger.exception("consolidate_audio: failed to delete audio objects")
