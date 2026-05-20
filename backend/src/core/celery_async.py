from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from celery.signals import worker_process_shutdown

from src.database import close_db

_worker_loop: asyncio.AbstractEventLoop | None = None


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    loop = get_or_create_worker_loop()
    loop.run_until_complete(coro)


def get_or_create_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop

    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)

    return _worker_loop


@worker_process_shutdown.connect
def shutdown_worker_loop(**_: Any) -> None:
    if _worker_loop is None or _worker_loop.is_closed():
        return

    _worker_loop.run_until_complete(close_db())
    _worker_loop.close()
