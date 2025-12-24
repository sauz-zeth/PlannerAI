#!/bin/bash

# Скрипт для запуска backend в режиме разработки
cd "$(dirname "$0")"
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
