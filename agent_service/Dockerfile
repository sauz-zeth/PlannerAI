FROM python:3.12-slim

WORKDIR /app

# Устанавливаем uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Копируем pyproject.toml и устанавливаем зависимости
COPY agent_service/pyproject.toml ./
COPY shared ./shared
COPY agent_service ./agent_service

# Компилируем и устанавливаем зависимости
RUN uv pip compile pyproject.toml -o requirements.txt \
    && uv pip install --system -r requirements.txt

ENV PYTHONPATH=/app

# Примечание: agent_service больше не имеет HTTP-сервера,
# это библиотека, используемая backend_service
CMD ["python", "-c", "print('Agent service library - no standalone server')"]

