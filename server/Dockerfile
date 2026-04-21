# syntax=docker/dockerfile:1.7

# ============================================================================
# Yüz Tanıma — Server container
# Used by docker-compose (dev) and the production VPS deploy.
# ============================================================================
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build dependencies for face_recognition / Pillow / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libopenblas-dev \
    libboost-all-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache-friendly deps install
COPY requirements.txt .
RUN pip install --upgrade pip wheel && pip install -r requirements.txt

COPY . .

RUN useradd --system --create-home --uid 1001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:5000/health || exit 1

# Default: gunicorn under eventlet (for Flask-SocketIO compatibility).
# Dev overrides this in docker-compose with `python run.py`.
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "app:create_app()"]