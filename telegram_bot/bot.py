"""Главный файл Telegram бота"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

try:
    from .config import TELEGRAM_BOT_TOKEN
    from .handlers import (
        start_command,
        login_command,
        check_command,
        events_command,
        help_command,
        button_callback,
        message_handler,
        voice_handler,
    )
except ImportError:
    from config import TELEGRAM_BOT_TOKEN
    from handlers import (
        start_command,
        login_command,
        check_command,
        events_command,
        help_command,
        button_callback,
        message_handler,
        voice_handler,
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("❌ Что-то пошло не так. Попробуй ещё раз.")
        except Exception:
            pass


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start",  start_command))
    application.add_handler(CommandHandler("login",  login_command))
    application.add_handler(CommandHandler("check",  check_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("help",   help_command))

    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    application.add_error_handler(error_handler)

    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
