"""Конфигурация для Telegram бота"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

# Backend API
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# OpenAI Whisper (для расшифровки голосовых сообщений)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Проверка наличия обязательных переменных
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN обязателен для работы бота")






