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

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости через uv
RUN uv sync --frozen

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uv", "run", "uvicorn", "backend_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
