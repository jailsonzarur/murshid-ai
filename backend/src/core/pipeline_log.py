from __future__ import annotations

import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("pipeline")

_in_flight: dict[str, int] = defaultdict(int)


def short(value: Any) -> str:
    return str(value)[:8]


@contextmanager
def stage(name: str, **fields: Any):
    """Marca início e fim de uma etapa, com quantas estão em voo neste processo.

    Sob gevent o contador é a concorrência real do worker. Sob prefork cada
    filho tem o seu, então ele fica sempre em 1.
    """
    detail = " ".join(f"{key}={value}" for key, value in fields.items())
    _in_flight[name] += 1
    started = time.perf_counter()
    logger.info("%s start %s in_flight=%d", name, detail, _in_flight[name])

    try:
        yield
    except Exception as exc:
        logger.warning(
            "%s failed %s %.2fs %s", name, detail, time.perf_counter() - started, type(exc).__name__
        )
        raise
    else:
        logger.info(
            "%s done %s %.2fs in_flight=%d",
            name,
            detail,
            time.perf_counter() - started,
            _in_flight[name],
        )
    finally:
        _in_flight[name] -= 1
