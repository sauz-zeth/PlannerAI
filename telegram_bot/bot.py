"""Главный файл Telegram бота"""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

try:
    from .config import TELEGRAM_BOT_TOKEN
    from .handlers import (
        start_command,
        login_command,
        check_command,
        events_command,
        upcoming_command,
        summary_command,
        status_command,
        create_event_command,
        search_command,
        free_slots_command,
        help_command,
        prompt_command
    )
except ImportError:
    # Для запуска напрямую
    from config import TELEGRAM_BOT_TOKEN
    from handlers import (
        start_command,
        login_command,
        check_command,
        events_command,
        upcoming_command,
        summary_command,
        status_command,
        create_event_command,
        search_command,
        free_slots_command,
        help_command,
        prompt_command
    )

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Если это обновление с сообщением, отправляем пользователю сообщение об ошибке
    if isinstance(update, Update) and update.effective_message:
        try:
            error_msg = "❌ Произошла ошибка. Попробуйте еще раз."
            
            # Для специфичных ошибок можно добавить более понятные сообщения
            if "Conflict" in str(context.error):
                error_msg = "⚠️ Другой экземпляр бота уже запущен. Остановите другие экземпляры."
            elif "BadRequest" in str(context.error):
                error_msg = "❌ Ошибка запроса. Проверьте правильность команды."
            
            await update.effective_message.reply_text(error_msg)
        except Exception as e:
            logger.error(f"Error while sending error message: {e}")


def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("upcoming", upcoming_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("create_event", create_event_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("free_slots", free_slots_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("prompt", prompt_command))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

