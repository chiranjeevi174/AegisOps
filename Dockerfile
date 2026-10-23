# syntax=docker/dockerfile:1

# Stage 1: Build virtual environment with uv
FROM python:3.12-slim-bookworm AS builder

# Install uv binary from official Astral distribution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install build dependencies for C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only into /app/.venv without project
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code and migration scripts
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY alembic.ini ./
COPY README.md ./

# Install application package in non-editable mode
RUN uv sync --frozen --no-dev

# Stage 2: Minimal hardened runtime image
FROM python:3.12-slim-bookworm AS runtime

# Create an unprivileged system user and group
RUN groupadd -g 10001 aegisops && \
    useradd -u 10001 -g aegisops -s /bin/bash -m aegisops

WORKDIR /app

# Install minimal runtime utilities (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and application from builder
COPY --from=builder --chown=aegisops:aegisops /app /app

# Set execution environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run as non-root user
USER aegisops:aegisops

EXPOSE 8000

# Health check using FastAPI liveness endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health/live || exit 1

# Explicit production startup command with uvicorn
CMD ["uvicorn", "aegisops.main:app", "--host", "0.0.0.0", "--port", "8000"]
