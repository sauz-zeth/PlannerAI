FROM python:3.12-slim

WORKDIR /app

# Общие системные зависимости: ffmpeg нужен для whisper в bot-сервисе, uv — менеджер пакетов
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY pyproject.toml README.md ./

RUN uv pip compile pyproject.toml -o requirements.txt \
    && uv pip install --system -r requirements.txt

COPY backend_service ./backend_service
COPY agent_service ./agent_service
COPY bot_service ./bot_service
COPY shared ./shared

ENV PYTHONPATH=/app

# По умолчанию запускаем backend; docker-compose переопределяет команду под нужный сервис
CMD ["uvicorn", "backend_service.main:app", "--host", "0.0.0.0", "--port", "8000"]


