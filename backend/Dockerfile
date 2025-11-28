# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace manifests
COPY pyproject.toml uv.lock ./

# Copy service manifests (for caching)
COPY backend/pyproject.toml backend/pyproject.toml
COPY agent/pyproject.toml agent/pyproject.toml
COPY shared/pyproject.toml shared/pyproject.toml

# Install ALL workspace deps (editable mode)
RUN uv sync --frozen --no-dev

# Copy full source code
COPY backend backend
COPY agent agent
COPY shared shared

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]