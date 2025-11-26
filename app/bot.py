import asyncio
import os
from io import BytesIO

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import tempfile

import whisper

from .agent import run_agent


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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
    # Whisper проще всего скормить путь к временному файлу.
    def _run_transcribe() -> str:
        with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            result = _whisper_model.transcribe(tmp.name, language="ru")
        return result.get("text", "").strip()

    text: str = await asyncio.to_thread(_run_transcribe)
    return text


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """
    Обработка голосовых сообщений:
    1. Скачиваем файл из Telegram.
    2. Отправляем в OpenAI для транскрибации.
    3. Пропускаем текст через минимального агента.
    4. Возвращаем текст пользователю.
    """
    await message.answer("🎙 Получил голосовое сообщение, распознаю текст...")

    # 1. Получаем файл
    voice = message.voice
    file = await bot.get_file(voice.file_id)

    buffer = BytesIO()
    await bot.download(file, buffer)
    buffer.seek(0)

    # 2. Транскрибация
    try:
        text = await transcribe_voice(buffer.read())
    except Exception as e:
        await message.answer(f"❌ Ошибка при транскрибации: {e}")
        return

    # 3. Агент
    agent_answer = await run_agent(text)

    # 4. Ответ пользователю
    await message.answer(
        f"📝 Распознанный текст:\n<code>{text}</code>\n\n{agent_answer}"
    )


@router.message(F.text)
async def handle_text(message: Message) -> None:
    """
    На всякий случай — если пользователь шлёт текст, а не голос.
    """
    agent_answer = await run_agent(message.text or "")
    await message.answer(agent_answer)


async def run_bot_polling() -> None:
    """
    Запуск aiogram-бота в режиме polling.
    Вызывать из FastAPI-приложения (startup-событие).
    """
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


