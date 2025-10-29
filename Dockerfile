FROM python:3.13-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY pyproject.toml .

# Установка Python зависимостей
RUN pip install --no-cache-dir -e .

# Копирование приложения
COPY . .

# Expose порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]