FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY pyproject.toml README.md ./

RUN uv pip compile pyproject.toml -o requirements.txt \
    && uv pip install --system -r requirements.txt

COPY backend_service ./backend_service
COPY agent_service ./agent_service
COPY shared ./shared

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

