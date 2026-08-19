# Multi-stage build for LightWMS backend
# Stage 1: Build stage
FROM python:3.11-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies from the pinned Debian release.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Resolve the complete dependency graph once and build a local wheelhouse.
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# Stage 2: Production stage
FROM python:3.11-slim-bookworm AS production

ARG LIGHTWMS_VERSION=unknown

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    APP_HOME=/app \
    LIGHTWMS_VERSION=${LIGHTWMS_VERSION}

WORKDIR $APP_HOME

# Keep the runtime tied to Debian bookworm so libvips package names are stable.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libvips42 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install only from the resolved wheelhouse produced by the builder.
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /var/log/lightwms /app/staticfiles /app/media \
    && chown -R appuser:appgroup /var/log/lightwms /app/staticfiles /app/media

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/')" || exit 1

# Default command
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2"]
