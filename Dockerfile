# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv для управления зависимостями
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml ./
COPY README.md ./

# Создаем виртуальное окружение и устанавливаем зависимости
RUN uv venv
RUN . .venv/bin/activate && uv pip install -e .

# Копируем остальные файлы приложения
COPY app/ ./app/
COPY .env.example .env

# Создаем директорию для моделей
RUN mkdir -p /app/models

# Открываем порт для FastAPI
EXPOSE 8000

# Активируем виртуальное окружение для всех команд
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запускаем приложение
CMD ["python", "-m", "app.main"]