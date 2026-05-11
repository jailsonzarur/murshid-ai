#!/bin/sh
set -e

echo "Starting worker..."
exec celery -A src.core.celery.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-info}"
