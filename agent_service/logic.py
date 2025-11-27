import asyncio
import os
from datetime import datetime
from typing import Optional

import parsedatetime as pdt
from openai import OpenAI


# BACKENDO
# Настройки подключения к локальному LM Studio
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-4b-2507")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")

# Глобальные объекты, чтобы не пересоздавать их при каждом вызове.
client = OpenAI(
    base_url=LM_STUDIO_BASE_URL,
    api_key=LM_STUDIO_API_KEY,  # любое непустое значение: LM Studio его не проверяет
)
cal = pdt.Calendar()

async def run_agent(text: str, requested_at: Optional[datetime]) -> str:
    """
    Асинхронный агент-планировщик:
    - пробует разобрать дату/время из текста с помощью parsedatetime;
    - отправляет запрос в OpenAI Chat Completions и возвращает краткий анализ.
    """
    # На будущее: если понадобится реальный асинхронный I/O, здесь уже есть async-контекст
    await asyncio.sleep(0)

    cleaned = text.strip()
    if not cleaned:
        return "Я получил пустой текст."

    reference_time = requested_at or datetime.utcnow()

    # Пробуем вытащить дату из текста на основе времени запроса
    dt, parsed = cal.parseDT(cleaned, sourceTime=reference_time)
    parsed_date = dt if parsed else reference_time

    # LLM-обработка через локальный LM Studio
    resp = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты — агент-планировщик, помогаешь пользователю формулировать события для календаря. "
                    f"Текущее время запроса: {reference_time}.\n"
                    f"Распознанная дата/время в тексте: {parsed_date}.\n"
                    "Отвечай строго в структурированном текстовом формате (НЕ JSON, НЕ списки).\n\n"
                           "Формат ответа:\n\n"
                           "Действие: <краткое намерение пользователя>\n"
                           "Название: <краткое название события>\n"
                    "Время: <точная дата (день, месяц, день недели)> <точное время начала (в формате XX:XX))> - "
                    "<точное время конца, если оно есть (в формате XX:XX)>\n"
                ),
            },
            {"role": "user", "content": cleaned},
        ],
    )

    summary = resp.choices[0].message.content
    return f"{summary}\n"

