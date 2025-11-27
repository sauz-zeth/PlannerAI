import asyncio
import os
import tempfile
from io import BytesIO
from typing import Any, Dict

import httpx
import whisper
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from dotenv import load_dotenv

# Загружаем переменные окружения из .env, если файл существует
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_SERVICE_URL = os.getenv("BACKEND_SERVICE_URL", "http://127.0.0.1:8000")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в переменных окружения")


bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher()
router = Router()
dp.include_router(router)

# Загружаем локальную модель Whisper один раз при импорте модуля.
# Можно поменять "base" на "small"/"medium"/"large-v3" при необходимости.
_whisper_model = whisper.load_model("base")

async def transcribe_voice(file_bytes: bytes) -> str:
    """
    Транскрибация голосового сообщения через локальную модель Whisper.
    Требуется установленный ffmpeg в системе/контейнере.
    """

    def _run_transcribe() -> str:
        with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            result = _whisper_model.transcribe(tmp.name, language="ru")
        return result.get("text", "").strip()

    text: str = await asyncio.to_thread(_run_transcribe)
    return text


async def request_agent(text: str, requested_at) -> str:
    """
    Проксируем запрос к backend-сервису.
    """
    payload: Dict[str, Any] = {
        "text": text,
        "requested_at": requested_at.isoformat() if requested_at else None,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_SERVICE_URL.rstrip('/')}/agent",
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"❌ Агент недоступен: {exc}"

    data = response.json()
    return data.get("result") or "❌ Агент вернул пустой ответ."


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """
    Обработка голосовых сообщений:
    1. Скачиваем файл из Telegram.
    2. Транскрибируем локальным Whisper.
    3. Отправляем текст на backend.
    4. Возвращаем итог пользователю.
    """
    await message.answer("🎙 Получил голосовое сообщение, распознаю текст...")

    voice = message.voice
    if not voice:
        await message.answer("❌ Ошибка: голосовое сообщение не найдено")
        return

    file = await bot.get_file(voice.file_id)

    buffer = BytesIO()
    await bot.download(file, buffer)
    buffer.seek(0)

    try:
        text = await transcribe_voice(buffer.read())
    except Exception as exc:  # noqa: BLE001 - хотим вернуть пользователю текст ошибки
        await message.answer(f"❌ Ошибка при транскрибации: {exc}")
        return

    agent_answer = await request_agent(text, message.date)

    await message.answer(
        f"📝 Распознанный текст:\n<code>{text}</code>\n\n{agent_answer}"
    )


@router.message(F.text)
async def handle_text(message: Message) -> None:
    """
    На всякий случай — если пользователь шлёт текст, а не голос.
    """
    agent_answer = await request_agent(message.text or "", message.date)
    await message.answer(agent_answer)


async def run_bot_polling() -> None:
    """
    Запуск aiogram-бота в режиме polling.
    """
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(run_bot_polling())


