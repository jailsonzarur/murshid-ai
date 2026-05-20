#!/bin/sh
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting application..."
if [ "${DEV_RELOAD:-0}" = "1" ]; then
  exec uv run uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir /app/src \
    --reload-dir /app/alembic
fi

exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
