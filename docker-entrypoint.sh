#!/bin/sh
set -e

# ensure env defaults
: ${PORT:=8000}

# Run migrations and collectstatic (ignore failures in case DB not ready)
echo "Running migrations..."
python manage.py migrate --noinput || echo "migrate failed"
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "collectstatic failed"

echo "Starting Gunicorn on port ${PORT}"
exec gunicorn myproject.wsgi:application --bind 0.0.0.0:${PORT} --workers 3 --log-level info
