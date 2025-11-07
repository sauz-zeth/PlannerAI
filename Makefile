.PHONY: help build up down restart logs shell db-shell ollama-pull clean

help: ## Показать эту справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	docker-compose build

up: ## Запустить все сервисы
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 5
	@echo "Services started! Check logs with 'make logs'"

down: ## Остановить все сервисы
	docker-compose down

restart: ## Перезапустить все сервисы
	docker-compose restart

logs: ## Показать логи всех сервисов
	docker-compose logs -f

logs-app: ## Показать логи только приложения
	docker-compose logs -f app

shell: ## Открыть shell в контейнере приложения
	docker-compose exec app /bin/bash

db-shell: ## Открыть psql в PostgreSQL
	docker-compose exec postgres psql -U calendar_user -d calendar_ai

ollama-pull: ## Загрузить модель Ollama
	docker-compose exec ollama ollama pull llama3.2:3b
	@echo "Model downloaded! You can also try: mistral:7b"

ollama-models: ## Показать загруженные модели Ollama
	docker-compose exec ollama ollama list

init: build up ollama-pull ## Первоначальная настройка (build + up + pull model)
	@echo "Setup complete! Bot is ready to use."
	@echo "Don't forget to set TELEGRAM_BOT_TOKEN in .env file"

clean: ## Остановить и удалить все контейнеры и volumes
	docker-compose down -v
	docker system prune -f

rebuild: clean build up ## Полная пересборка

status: ## Показать статус сервисов
	docker-compose ps

dev: ## Запуск в режиме разработки (с hot reload)
	docker-compose up

prod: ## Запуск в production режиме
	docker-compose up -d --build

test: ## Запустить тесты
	docker-compose exec app pytest

format: ## Форматировать код
	docker-compose exec app black app/
	docker-compose exec app ruff check app/ --fix

backup-db: ## Создать бэкап базы данных
	docker-compose exec postgres pg_dump -U calendar_user calendar_ai > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Восстановить базу данных из бэкапа (использование: make restore-db FILE=backup.sql)
	docker-compose exec -T postgres psql -U calendar_user calendar_ai < $(FILE)