#!/bin/sh
set -eu

echo '{"level":"INFO","logger":"busreserve.entrypoint","message":"Running database migrations"}'
flask db upgrade

if [ "${SEED_ON_STARTUP:-false}" = "true" ]; then
    echo '{"level":"INFO","logger":"busreserve.entrypoint","message":"Running idempotent seed script"}'
    flask seed
fi

exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --log-level "${LOG_LEVEL:-info}" \
    wsgi:app
