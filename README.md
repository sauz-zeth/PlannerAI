# 🤖 Calendar AI Bot

AI-powered Telegram bot для управления календарем и расписанием.

## ✨ Возможности

- 📅 Интеллектуальное управление расписанием через чат
- 🎤 Поддержка голосовых сообщений
- 🔄 Синхронизация с внешними календарями (iCal)
- 📤 Экспорт календаря в формате iCal
- 🤖 Локальная LLM (полная приватность данных)
- 🔍 Умный поиск свободного времени
- ⚡ Автоматическое предложение переносов событий

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Telegram Bot Token (получить у [@BotFather](https://t.me/botfather))

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone <your-repo-url>
cd calendar-ai-bot
```

2. **Создайте .env файл:**
```bash
cp .env.example .env
```

3. **Отредактируйте .env и добавьте токен бота:**
```env
TELEGRAM_BOT_TOKEN=your_actual_token_here
```

4. **Запустите скрипт установки:**

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Или с помощью Make:**
```bash
make init
```

**Или вручную:**
```bash
docker-compose build
docker-compose up -d
docker-compose exec ollama ollama pull llama3.2:3b
```

5. **Готово!** Откройте Telegram и напишите вашему боту `/start`

## 📖 Использование

### Команды бота

- `/start` - Начать работу с ботом
- `/help` - Справка по использованию
- `/settings` - Настройки и ссылка на календарь
- `/calendar` - Показать календарь

### Примеры запросов

- "Хочу начать ходить в зал по утрам"
- "Найди свободное время на встречу завтра"
- "Перенеси встречу с Иваном на послезавтра"
- "Что у меня в расписании на эту неделю?"

## 🛠️ Разработка

### Структура проекта

```
calendar-ai-bot/
├── app/
│   ├── bot/          # Telegram bot handlers
│   ├── api/          # FastAPI routes
│   ├── llm/          # LLM integration
│   ├── services/     # Business logic
│   ├── db/           # Database models
│   └── utils/        # Utilities
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

### Команды разработки

**С помощью Make:**
```bash
make dev          # Запуск в режиме разработки
make logs         # Смотреть логи
make logs-app     # Логи только бота
make shell        # Shell в контейнере
make db-shell     # PostgreSQL консоль
make test         # Запустить тесты
make format       # Форматировать код
```

**Без Make:**
```bash
docker-compose up                    # Запуск с логами
docker-compose logs -f               # Все логи
docker-compose logs -f app           # Логи бота
docker-compose exec app bash         # Shell
docker-compose exec postgres psql -U calendar_user -d calendar_ai
```

### Локальная разработка (без Docker)

```bash
# Установка зависимостей
uv venv
source .venv/bin/activate
uv pip install -e .

# Запуск PostgreSQL и Redis локально
# (через Docker, brew, apt и т.д.)

# Запуск Ollama
ollama serve
ollama pull llama3.2:3b

# Запуск приложения
python -m app.main
```

## 🔧 Конфигурация

Все настройки в `.env` файле:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_token

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/calendar_ai

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# API
API_PORT=8000
DEBUG=True
```

### Выбор LLM модели

По умолчанию используется `llama3.2:3b` (легкая, быстрая).

Альтернативы:
```bash
# Более мощная модель
docker-compose exec ollama ollama pull mistral:7b

# Обновите в .env
OLLAMA_MODEL=mistral:7b

# Перезапустите
docker-compose restart app
```

## 📊 Мониторинг

### Проверка здоровья сервисов

```bash
# Статус всех сервисов
docker-compose ps

# Health check API
curl http://localhost:8000/health

# Проверка базы данных
docker-compose exec postgres pg_isready -U calendar_user

# Проверка Ollama
curl http://localhost:11434/api/tags
```

### Логи

```bash
# Все логи
docker-compose logs -f

# Только ошибки
docker-compose logs --tail=100 | grep ERROR

# Конкретный сервис
docker-compose logs -f app
docker-compose logs -f postgres
```

## 🗄️ База данных

### Backup

```bash
# Создать backup
docker-compose exec postgres pg_dump -U calendar_user calendar_ai > backup.sql

# Или с Make
make backup-db
```

### Restore

```bash
# Восстановить из backup
docker-compose exec -T postgres psql -U calendar_user calendar_ai < backup.sql

# Или с Make
make restore-db FILE=backup.sql
```

## 🐛 Решение проблем

### Бот не отвечает

1. Проверьте логи: `docker-compose logs -f app`
2. Убедитесь что токен правильный в `.env`
3. Проверьте что все сервисы запущены: `docker-compose ps`

### Ошибка подключения к БД

```bash
# Проверьте статус PostgreSQL
docker-compose logs postgres

# Пересоздайте базу
docker-compose down -v
docker-compose up -d
```

### Ollama не работает / медленно

```bash
# Проверьте статус
docker-compose exec ollama ollama list

# Если модель не загружена
docker-compose exec ollama ollama pull llama3.2:3b

# Для GPU поддержки раскомментируйте в docker-compose.yml
```

## 📝 TODO

- [ ] Реализация LLM обработки
- [ ] iCalendar интеграция
- [ ] Голосовые сообщения (Whisper)
- [ ] Умный планировщик
- [ ] Веб-интерфейс
- [ ] Тесты
- [ ] CI/CD

## 📄 Лицензия

MIT

## 🤝 Участие в разработке

Pull requests приветствуются!

## 📧 Контакты

Если есть вопросы или предложения - создайте Issue.