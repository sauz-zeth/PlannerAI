FROM python:3.12-slim

WORKDIR /app

# Устанавливаем системные зависимости: ffmpeg нужен для whisper
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Копируем pyproject.toml и устанавливаем зависимости
COPY bot_service/pyproject.toml ./
COPY shared ./shared
COPY bot_service ./bot_service

# Компилируем и устанавливаем зависимости
RUN uv pip compile pyproject.toml -o requirements.txt \
    && uv pip install --system -r requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "-m", "bot_service.main"]

