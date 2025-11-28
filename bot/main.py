import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from app.router import setup
from app.config import settings

async def main():
    bot = Bot(
        settings.TELEGRAM_BOT_TOKEN,
        parse_mode=ParseMode.HTML
    )

    dp = Dispatcher()
    setup(dp)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())