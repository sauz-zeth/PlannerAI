# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Устанавливаем рабочую директорию
WORKDIR /app

# Делаем пакеты доступными как корневые (app и backend_service)
ENV PYTHONPATH="/app:/app/backend_service"

# Копируем только нужные файлы для backend
COPY backend_service/ ./backend_service/
COPY agent_service/ ./agent_service/
COPY shared/ ./shared/

# Устанавливаем только зависимости для backend (без openai-whisper и aiogram)
RUN uv pip install --system \
    fastapi>=0.115.0 \
    uvicorn[standard]>=0.30.0 \
    openai>=1.0.0 \
    parsedatetime>=2.6 \
    pydantic>=2.8.0

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "backend_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
