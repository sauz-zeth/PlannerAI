#!/bin/bash

# Скрипт для деплоя backend на VPS
# Использование: ./deploy.sh [VPS_USER] [VPS_HOST] [DEPLOY_PATH]

set -e

VPS_USER=${1:-${VPS_USER:-root}}
VPS_HOST=${2:-${VPS_HOST}}
DEPLOY_PATH=${3:-${VPS_DEPLOY_PATH:-~/plannerAI}}

if [ -z "$VPS_HOST" ]; then
    echo "Ошибка: необходимо указать VPS_HOST"
    echo "Использование: ./deploy.sh [VPS_USER] [VPS_HOST] [DEPLOY_PATH]"
    exit 1
fi

echo "🚀 Начинаю деплой на $VPS_USER@$VPS_HOST:$DEPLOY_PATH"

# Проверяем подключение
echo "📡 Проверяю подключение к серверу..."
ssh -o ConnectTimeout=5 $VPS_USER@$VPS_HOST "echo 'Подключение успешно'" || {
    echo "❌ Не удалось подключиться к серверу"
    exit 1
}

# Создаем директорию на сервере, если её нет
echo "📁 Создаю директорию на сервере..."
ssh $VPS_USER@$VPS_HOST "mkdir -p $DEPLOY_PATH"

# Копируем файлы
echo "📦 Копирую файлы на сервер..."
rsync -avz --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='.venv' \
    --exclude='venv' \
    ./ $VPS_USER@$VPS_HOST:$DEPLOY_PATH/

# Выполняем деплой на сервере
echo "🔧 Выполняю деплой на сервере..."
ssh $VPS_USER@$VPS_HOST << EOF
    set -e
    cd $DEPLOY_PATH
    
    # Проверяем наличие Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker не установлен. Устанавливаю..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
    fi
    
    # Проверяем наличие docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo "❌ docker-compose не установлен. Устанавливаю..."
        apt-get update
        apt-get install -y docker-compose-plugin
    fi
    
    # Останавливаем старые контейнеры
    echo "🛑 Останавливаю старые контейнеры..."
    docker compose down || true
    
    # Собираем и запускаем новые контейнеры
    echo "🏗️  Собираю образы..."
    docker compose build --no-cache
    
    echo "🚀 Запускаю контейнеры..."
    docker compose up -d
    
    # Очищаем старые образы
    echo "🧹 Очищаю старые образы..."
    docker image prune -f
    
    # Показываем статус
    echo "📊 Статус контейнеров:"
    docker compose ps
    
    echo "✅ Деплой завершен успешно!"
EOF

echo "🎉 Деплой завершен!"

