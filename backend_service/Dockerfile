FROM python:3.12-slim

WORKDIR /app

# Устанавливаем uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Копируем структуру проекта
COPY backend_service/pyproject.toml ./pyproject.toml
COPY shared ./shared
COPY agent_service ./agent_service
COPY backend_service ./backend_service

# Компилируем зависимости в requirements.txt и устанавливаем их
# requirements.txt создается временно, но зависимости устанавливаются в систему
RUN uv pip compile pyproject.toml -o /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
