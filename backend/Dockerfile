# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace manifests (if building from root)
COPY pyproject.toml uv.lock ./

# Copy backend service manifest (for caching)
COPY backend/pyproject.toml backend/pyproject.toml

# Install dependencies for backend package
RUN uv sync --frozen --no-dev --package backend

# Copy backend source code
COPY backend/ ./backend/

# Set working directory to backend for running the app
WORKDIR /app/backend

EXPOSE 8000

# Use uv run to ensure proper environment
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]