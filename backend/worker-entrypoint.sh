#!/bin/sh
set -e

export MEDIA_CONCURRENCY="${MEDIA_CONCURRENCY:-2}"
export TRANSCRIBE_CONCURRENCY="${TRANSCRIBE_CONCURRENCY:-6}"
export TRANSCRIBE_POOL="${TRANSCRIBE_POOL:-prefork}"
export SUMMARY_CONCURRENCY="${SUMMARY_CONCURRENCY:-2}"
export SUMMARY_POOL="${SUMMARY_POOL:-prefork}"
export CELERY_LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"

CONF=/app/supervisord.conf

echo "Starting workers: media prefork (-c $MEDIA_CONCURRENCY), transcribe $TRANSCRIBE_POOL (-c $TRANSCRIBE_CONCURRENCY), summary $SUMMARY_POOL (-c $SUMMARY_CONCURRENCY)"

if [ "${DEV_RELOAD:-0}" != "1" ]; then
  exec supervisord -c "$CONF"
fi

supervisord -c "$CONF" &
supervisor_pid="$!"
trap 'kill -TERM "$supervisor_pid" 2>/dev/null; wait "$supervisor_pid"; exit 0' INT TERM

marker=/tmp/worker-reload-marker
touch "$marker"

while kill -0 "$supervisor_pid" 2>/dev/null; do
  sleep 2
  if [ -n "$(find /app/src -type f -name '*.py' -newer "$marker" -print -quit)" ]; then
    echo "Python source changed. Restarting workers..."
    touch "$marker"
    supervisorctl -c "$CONF" restart all || true
  fi
done

wait "$supervisor_pid"
