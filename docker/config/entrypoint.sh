#!/bin/bash
set -e

echo "============================================"
echo "  LightWMS Unified Container Starting"
echo "============================================"

# Create log directories with proper permissions
echo "[1/6] Creating log directories..."
mkdir -p /var/log/supervisor /var/log/nginx /var/log/lightwms

# Pre-create log files with correct ownership for appuser processes
touch /var/log/lightwms/gunicorn.log \
      /var/log/lightwms/gunicorn_access.log \
      /var/log/lightwms/gunicorn_error.log \
      /var/log/lightwms/nextjs.log \
      /var/log/lightwms/nextjs_error.log \
      /var/log/lightwms/app.log

chown -R appuser:appgroup /var/log/lightwms 2>/dev/null || true
chown -R www-data:www-data /var/log/nginx 2>/dev/null || true
chmod 755 /var/log/supervisor /var/log/nginx /var/log/lightwms
chmod 644 /var/log/lightwms/*.log 2>/dev/null || true

# Ensure media and static directories exist
echo "[2/6] Ensuring media and static directories..."
mkdir -p /app/backend/media /app/backend/staticfiles
chown -R appuser:appgroup /app/backend/media /app/backend/staticfiles 2>/dev/null || true

# Wait for database to be ready
echo "[3/6] Waiting for database..."
max_retries=30
retry_count=0

cd /app/backend

while ! python manage.py check --database default > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo "ERROR: Database connection failed after $max_retries attempts"
        echo "Please check your database configuration:"
        echo "  - POSTGRES_HOST: ${POSTGRES_HOST:-not set}"
        echo "  - POSTGRES_PORT: ${POSTGRES_PORT:-not set}"
        echo "  - POSTGRES_DB: ${POSTGRES_DB:-not set}"
        exit 1
    fi
    echo "  Database not ready, waiting... ($retry_count/$max_retries)"
    sleep 2
done
echo "  Database is ready!"

# Run database migrations
echo "[4/6] Running database migrations..."
python manage.py migrate --noinput
if [ $? -ne 0 ]; then
    echo "ERROR: Database migration failed"
    exit 1
fi
echo "  Migrations completed successfully"

# Collect static files
echo "[5/6] Collecting static files..."
python manage.py collectstatic --noinput --clear
if [ $? -ne 0 ]; then
    echo "WARNING: Static file collection had issues, continuing..."
fi
echo "  Static files collected"

# Create superuser if requested
if [ "$CREATE_SUPERUSER" = "true" ] && [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "[6/6] Creating superuser..."
    python manage.py createsuperuser --noinput 2>/dev/null && echo "  Superuser created" || echo "  Superuser already exists or creation skipped"
else
    echo "[6/6] Skipping superuser creation (CREATE_SUPERUSER not set to true)"
fi

echo "============================================"
echo "  Starting services..."
echo "============================================"
echo "  - Nginx (port 80)"
echo "  - Gunicorn (port 8000)"
echo "  - Next.js (port 3000)"
echo "============================================"

exec "$@"
