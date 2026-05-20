#!/bin/sh
set -e

echo "Starting worker..."
if [ "${DEV_RELOAD:-0}" = "1" ]; then
  marker="/tmp/worker-reload-marker"

  while true; do
    touch "$marker"
    celery -A src.core.celery.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-info}" &
    worker_pid="$!"

    trap 'kill "$worker_pid" 2>/dev/null || true; exit 0' INT TERM

    while kill -0 "$worker_pid" 2>/dev/null; do
      sleep 2
      if [ -n "$(find /app/src -type f -name '*.py' -newer "$marker" -print -quit)" ]; then
        echo "Python source changed. Restarting worker..."
        kill "$worker_pid" 2>/dev/null || true
        wait "$worker_pid" 2>/dev/null || true
        break
      fi
    done
  done
fi

exec celery -A src.core.celery.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-info}"
