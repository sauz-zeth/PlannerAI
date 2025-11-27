# Инструкция по деплою backend на VPS

## Предварительные требования

1. VPS с установленным Docker и Docker Compose
2. SSH доступ к серверу
3. Переменные окружения настроены в `.env` файле

## Быстрый старт

### Вариант 1: Автоматический деплой через GitHub Actions

1. Настройте секреты в GitHub:
   - `VPS_SSH_KEY` - приватный SSH ключ для доступа к VPS
   - `VPS_HOST` - IP адрес или домен VPS
   - `VPS_USER` - пользователь для SSH (обычно `root`)
   - `VPS_DEPLOY_PATH` - путь на сервере для деплоя (по умолчанию `~/plannerAI`)

2. При пуше в ветку `backend` автоматически запустится деплой

### Вариант 2: Ручной деплой через скрипт

```bash
# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите деплой
./deploy.sh [VPS_USER] [VPS_HOST] [DEPLOY_PATH]

# Пример:
./deploy.sh root 192.168.1.100 ~/plannerAI
```

### Вариант 3: Ручной деплой через SSH

```bash
# 1. Скопируйте файлы на сервер
rsync -avz --exclude='.git' ./ user@vps:~/plannerAI/

# 2. Подключитесь к серверу
ssh user@vps

# 3. Перейдите в директорию проекта
cd ~/plannerAI

# 4. Создайте .env файл с необходимыми переменными
nano .env

# 5. Запустите контейнеры
docker compose up -d --build
```

## Настройка переменных окружения

Создайте файл `.env` на сервере в директории проекта:

```env
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=qwen/qwen3-4b-2507
LM_STUDIO_API_KEY=lm-studio
```

## Установка Docker на VPS (если не установлен)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Установка docker-compose
apt-get update
apt-get install -y docker-compose-plugin
```

## Настройка Nginx (опционально)

1. Скопируйте `nginx.conf` в `/etc/nginx/sites-available/ai-planner-backend`
2. Отредактируйте `server_name` на ваш домен или IP
3. Создайте симлинк:
   ```bash
   ln -s /etc/nginx/sites-available/ai-planner-backend /etc/nginx/sites-enabled/
   ```
4. Проверьте конфигурацию и перезапустите nginx:
   ```bash
   nginx -t
   systemctl reload nginx
   ```

## Управление сервисом

### Docker Compose команды

```bash
# Запуск
docker compose up -d

# Остановка
docker compose down

# Просмотр логов
docker compose logs -f

# Перезапуск
docker compose restart

# Пересборка и запуск
docker compose up -d --build
```

### Systemd (если используете backend.service)

```bash
# Включить автозапуск
sudo systemctl enable backend

# Запустить
sudo systemctl start backend

# Остановить
sudo systemctl stop backend

# Статус
sudo systemctl status backend

# Логи
sudo journalctl -u backend -f
```

## Проверка работы

После деплоя проверьте:

```bash
# Health check
curl http://localhost:8000/health

# Или с внешнего IP
curl http://YOUR_VPS_IP:8000/health
```

## Мониторинг

```bash
# Статус контейнеров
docker compose ps

# Использование ресурсов
docker stats

# Логи
docker compose logs -f backend
```

## Обновление

При обновлении кода:

1. **Через GitHub Actions**: просто запушьте изменения в ветку `backend`
2. **Вручную**: выполните `deploy.sh` снова или:
   ```bash
   ssh user@vps "cd ~/plannerAI && git pull && docker compose up -d --build"
   ```

## Troubleshooting

### Контейнер не запускается

```bash
# Проверьте логи
docker compose logs backend

# Проверьте конфигурацию
docker compose config
```

### Порт занят

```bash
# Проверьте, что использует порт 8000
sudo lsof -i :8000

# Или измените порт в docker-compose.yml
```

### Проблемы с переменными окружения

```bash
# Проверьте .env файл
cat .env

# Проверьте переменные в контейнере
docker compose exec backend env
```

