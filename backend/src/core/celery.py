from celery import Celery
from decouple import config


def _get_bool_config(name: str, *, default: bool = False) -> bool:
    value = str(config(name, default=str(default))).strip().lower()
    return value in {"1", "true", "yes", "on"}


redis_url = str(config("REDIS_URL", default="redis://redis:6379/0")).strip()
broker_url = str(config("CELERY_BROKER_URL", default=redis_url)).strip()
result_backend = str(config("CELERY_RESULT_BACKEND", default=broker_url)).strip()

celery_app = Celery(
    "api_v2",
    broker=broker_url,
    backend=result_backend,
    include=["src.features.exams.tasks", "src.features.resolutions.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    result_serializer="json",
    task_always_eager=_get_bool_config("CELERY_TASK_ALWAYS_EAGER", default=False),
    task_eager_propagates=True,
    task_serializer="json",
    task_track_started=True,
    timezone="UTC",
)
