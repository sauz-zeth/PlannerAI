import asyncio

import parsedatetime as pdt
from openai import OpenAI

# Глобальные объекты, чтобы не пересоздавать на каждый вызов.
# Настраиваем клиента на локальный LM Studio, который поднимает OpenAI-совместимый API.
client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio",  # любое непустое значение, LM Studio его не проверяет
)
cal = pdt.Calendar()


async def run_agent(text: str) -> str:
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

    # Попробовать достать дату
    dt, parsed = cal.parseDT(cleaned)
    date_info = f"📅 Дата найдена: {dt}" if parsed else "⛔ Дата не найдена"

    # LLM-обработка через локальный LM Studio
    # Важно: имя модели должно совпадать с тем, что указано в LM Studio (обычно "local-model").
    resp = client.chat.completions.create(
        model="qwen/qwen3-4b-2507",
        messages=[
            {
                "role": "system",
                "content": "Ты — мини-планировщик. Кратко объясняй задачу пользователя.",
            },
            {"role": "user", "content": cleaned},
        ],
    )

    summary = resp.choices[0].message.content
    return f"🎯 Анализ:\n{summary}\n\n{date_info}"


