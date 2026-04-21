# AI Planner Backend

Backend для AI Planner с интеграцией Google Calendar и Telegram ботом для тестирования.

## Структура проекта

- `backend/` - FastAPI бэкенд с API для работы с Google Calendar
- `telegram_bot/` - Telegram бот для тестирования API

## Быстрый старт

### Backend

1. Установите зависимости:
```bash
cd backend
uv sync
```

2. Настройте переменные окружения в `.env`:
```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://ai_planner:ai_planner_pass@localhost:5432/ai_planner
```

3. Запустите бэкенд:
```bash
./run.sh
```

### Telegram бот

1. Установите зависимости:
```bash
cd telegram_bot
uv sync
```

2. Убедитесь, что в `.env` установлен `TELEGRAM_BOT_TOKEN` и `BACKEND_API_URL`

3. Запустите бота:
```bash
./run.sh
```

## API документация

После запуска бэкенда API документация доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Telegram бот

Бот позволяет:
- Авторизоваться через Google Calendar (deep link поддерживается)
- Тестировать все API endpoints календаря
- Управлять событиями через удобный интерфейс

Подробная документация: [telegram_bot/README.md](telegram_bot/README.md)

## Docker

Для запуска через Docker:

```bash
docker-compose up -d
```
