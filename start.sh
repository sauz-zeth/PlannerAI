#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Calendar AI Bot - Setup Script         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен. Установите Docker и попробуйте снова.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker установлен${NC}"

# Проверка .env файла
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Файл .env не найден. Создаю из .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  ВАЖНО: Отредактируйте .env и добавьте TELEGRAM_BOT_TOKEN!${NC}"
    echo -e "${YELLOW}   Получить токен можно у @BotFather в Telegram${NC}"
    read -p "Нажмите Enter после редактирования .env файла..."
fi

# Проверка токена
if grep -q "your_bot_token_here" .env; then
    echo -e "${RED}❌ Токен бота не настроен в .env файле!${NC}"
    echo -e "${YELLOW}   Откройте .env и замените 'your_bot_token_here' на реальный токен${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Конфигурация найдена${NC}"
echo ""

# Сборка образов
echo -e "${YELLOW}📦 Сборка Docker образов...${NC}"
docker-compose build

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при сборке образов${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Образы собраны${NC}"
echo ""

# Запуск сервисов
echo -e "${YELLOW}🚀 Запуск сервисов...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при запуске сервисов${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Сервисы запущены${NC}"
echo ""

# Ожидание запуска сервисов
echo -e "${YELLOW}⏳ Ожидание запуска сервисов (30 сек)...${NC}"
sleep 30

# Загрузка модели Ollama
echo -e "${YELLOW}📥 Загрузка LLM модели (это может занять несколько минут)...${NC}"
docker-compose exec -T ollama ollama pull llama3.2:3b

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при загрузке модели${NC}"
    echo -e "${YELLOW}   Попробуйте вручную: docker-compose exec ollama ollama pull llama3.2:3b${NC}"
else
    echo -e "${GREEN}✅ Модель загружена${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          🎉 Установка завершена!          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Сервисы запущены:${NC}"
echo -e "  📱 Telegram Bot: активен"
echo -e "  🌐 API: http://localhost:8000"
echo -e "  🗄️  PostgreSQL: localhost:5432"
echo -e "  🔴 Redis: localhost:6379"
echo -e "  🤖 Ollama: http://localhost:11434"
echo ""
echo -e "${YELLOW}Полезные команды:${NC}"
echo -e "  docker-compose logs -f          # Смотреть логи"
echo -e "  docker-compose logs -f app      # Логи только бота"
echo -e "  docker-compose restart          # Перезапуск"
echo -e "  docker-compose down             # Остановка"
echo -e "  docker-compose exec app bash    # Shell в контейнере"
echo ""
echo -e "${GREEN}Откройте Telegram и напишите вашему боту /start${NC}"
echo ""