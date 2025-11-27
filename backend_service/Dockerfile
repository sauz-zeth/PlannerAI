FROM python:3.12-slim

WORKDIR /app

# Устанавливаем uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Копируем pyproject.toml и устанавливаем зависимости
COPY backend_service/pyproject.toml ./
COPY shared ./shared
COPY agent_service ./agent_service
COPY backend_service ./backend_service

# Компилируем и устанавливаем зависимости
RUN uv pip compile pyproject.toml -o requirements.txt \
    && uv pip install --system -r requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
