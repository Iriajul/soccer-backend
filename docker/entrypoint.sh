#!/usr/bin/env sh
# Container entrypoint: apply migrations, bootstrap the super admin (mirrors
# NestJS onModuleInit), collect static for the admin, then serve on :3000.
set -e

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Bootstrapping super admin (if none exists)..."
python manage.py bootstrap_superadmin || true

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting gunicorn on :3000..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:3000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
