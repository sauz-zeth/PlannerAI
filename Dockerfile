FROM python:3.12-slim

WORKDIR /app

# Устанавливаем системные зависимости: ffmpeg (для whisper) и uv (менеджер пакетов)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY pyproject.toml README.md ./

# Сначала компилируем зависимости из pyproject.toml в requirements.txt,
# затем ставим их в системное окружение контейнера
RUN uv pip compile pyproject.toml -o requirements.txt \
    && uv pip install --system -r requirements.txt

COPY app ./app

ENV PYTHONPATH=/app

EXPOSE 8000

# Запускаем FastAPI + aiogram-бот (polling поднимется при старте приложения)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


