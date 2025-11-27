## Архитектура

Монорепозитория содержит три компонента:

- `bot_service` — Telegram-бот (aiogram + локальный Whisper), который распознаёт голос и шлёт текст в backend.
- `backend_service` — FastAPI-приложение с публичным HTTP API; **оно напрямую вызывает агент как Python-библиотеку**.
- `agent_service` — модуль с логикой LangGraph/LLM (без собственного HTTP-сервера), который импортируется backend-ом.

Общие pydantic-схемы лежат в пакете `shared`.

## Переменные окружения

Создайте `.env` и заполните минимум:

- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота.
- `BACKEND_SERVICE_URL` — URL backend для бота (по умолчанию `http://127.0.0.1:8000`).
- `LM_STUDIO_BASE_URL` — URL локального LM Studio (`http://127.0.0.1:1234/v1`).
- `LM_STUDIO_MODEL` — имя модели в LM Studio (например, `qwen/qwen3-4b-2507`).

## Локальный запуск (несколько терминалов)

```bash
uv sync  # установить зависимости

# 1. Backend (агент вызывается из него напрямую)
uv run uvicorn backend_service.main:app --host 0.0.0.0 --port 8000

# 2. Бот
uv run python -m bot_service.main
```

Проверка:
- `GET http://localhost:8000/health` — backend.
- В Telegram напишите боту голос/текст.

## Docker / docker-compose

Файл `backend_service/Dockerfile` используется для прод-образа backend-а, а `Dockerfile` (в корне) — для бота. `docker-compose.yml` поднимает два контейнера:

```bash
docker compose up --build
```

Важно:

- LM Studio должен быть доступен по `http://host.docker.internal:1234/v1` (значение можно переопределить в `.env`).
- `bot` сервису нужны реальные токены (`TELEGRAM_BOT_TOKEN`).

## Структура каталогов

```
backend_service/   # FastAPI API (дергает агент как библиотеку)
agent_service/     # логика LLM (без HTTP сервера)
bot_service/       # aiogram + Whisper
shared/            # общие схемы
docker-compose.yml # оркестрация backend + bot
```
