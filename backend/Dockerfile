# =============================================================================
# Descomplicita - Backend Dockerfile (multi-stage)
# =============================================================================
# Production-ready Python FastAPI application for Railway deployment

# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --target /build/deps

# --- Stage 2: Production ---
FROM python:3.11-slim

LABEL build.timestamp="2026-03-07T00:00:00"

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /build/deps /app/deps
ENV PYTHONPATH="/app/deps:${PYTHONPATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Remove dev files from production image
RUN rm -f requirements-dev.txt && \
    rm -rf tests/ examples/ __pycache__/ .pytest_cache/

# Create non-root user and switch to it
RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

# Run with startup script for crash diagnostics
CMD ["python", "start.py"]
