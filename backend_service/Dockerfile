FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir uv

# Ставим базовые зависимости (могут быть пустыми)
COPY pyproject.toml README.md ./

RUN uv pip compile pyproject.toml -o requirements.txt \
    && uv pip install --system -r requirements.txt

EXPOSE 8000