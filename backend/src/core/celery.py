from celery import Celery
from decouple import config


def _patch_psycopg_for_gevent() -> None:
    """Sob gevent o psycopg2 espera o socket dentro da libpq, fora do alcance do
    monkey-patching — sem isto ele trava o hub inteiro durante cada query."""
    try:
        from gevent import monkey
    except ImportError:
        return

    if not monkey.is_module_patched("socket"):
        return

    from psycogreen.gevent import patch_psycopg

    patch_psycopg()


_patch_psycopg_for_gevent()


def _get_bool_config(name: str, *, default: bool = False) -> bool:
    value = str(config(name, default=str(default))).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get_int_config(name: str, *, default: int) -> int:
    try:
        return int(str(config(name, default=str(default))).strip())
    except ValueError:
        return default


redis_url = str(config("REDIS_URL", default="redis://redis:6379/0")).strip()
broker_url = str(config("CELERY_BROKER_URL", default=redis_url)).strip()
result_backend = str(config("CELERY_RESULT_BACKEND", default=broker_url)).strip()

celery_app = Celery(
    "api_v2",
    broker=broker_url,
    backend=result_backend,
    include=["src.features.lectures.tasks", "src.features.subjects.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    task_routes={
        "start_import_lecture_task": {"queue": "lectures"},
        "finalize_lecture_task": {"queue": "lectures"},
        "chunk_audio_task": {"queue": "audios"},
        "consolidate_audio_task": {"queue": "audios"},
        "transcribe_chunk_task": {"queue": "chunks"},
        "generate_lecture_summary_task": {"queue": "summaries"},
        "generate_lecture_mindmap_task": {"queue": "summaries"},
    },
    broker_connection_retry_on_startup=True,
    result_serializer="json",
    task_acks_late=True,
    broker_transport_options={
        "visibility_timeout": _get_int_config("CELERY_VISIBILITY_TIMEOUT", default=7200),
    },
    task_always_eager=_get_bool_config("CELERY_TASK_ALWAYS_EAGER", default=False),
    task_eager_propagates=True,
    task_serializer="json",
    task_track_started=True,
    timezone="UTC",
    worker_concurrency=_get_int_config("CELERY_CONCURRENCY", default=2),
    worker_max_tasks_per_child=_get_int_config("CELERY_MAX_TASKS_PER_CHILD", default=8),
    worker_prefetch_multiplier=1,
    task_soft_time_limit=_get_int_config("CELERY_SOFT_TIME_LIMIT", default=5400),
    task_time_limit=_get_int_config("CELERY_TIME_LIMIT", default=7200),
    result_expires=_get_int_config("CELERY_RESULT_EXPIRES", default=3600),
)
