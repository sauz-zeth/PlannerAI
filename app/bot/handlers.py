from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User
from app.bot.keyboards import get_main_menu, get_setup_keyboard
from app.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """Handle /start command"""
    telegram_id = message.from_user.id
    
    # Check if user exists
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        session.add(user)
        await session.commit()
        
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Я - AI-ассистент для управления твоим расписанием.\n\n"
            "Я помогу тебе:\n"
            "✅ Планировать события\n"
            "✅ Находить свободное время\n"
            "✅ Переносить встречи\n"
            "✅ Синхронизировать календари\n\n"
            "Давай начнем с настройки!",
            reply_markup=get_setup_keyboard()
        )
    else:
        await message.answer(
            f"С возвращением, {message.from_user.first_name}! 👋\n\n"
            "Чем могу помочь?",
            reply_markup=get_main_menu()
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command"""
    help_text = """
🤖 <b>Как пользоваться ботом:</b>

<b>Примеры команд:</b>
• "Хочу начать ходить в зал по утрам"
• "Найди свободное время на встречу завтра"
• "Перенеси встречу с Иваном на послезавтра"
• "Что у меня в расписании на эту неделю?"

<b>Команды:</b>
/start - Начать работу
/help - Справка
/settings - Настройки
/calendar - Показать календарь
/export - Экспортировать календарь

💡 Ты можешь отправлять как текстовые, так и голосовые сообщения!
    """
    await message.answer(help_text)


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    """Handle /settings command"""
    telegram_id = message.from_user.id
    
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Сначала используй /start для регистрации")
        return
    
    ical_url = f"{settings.ical_base_url}/{user.ical_subscription_token}.ics"
    
    settings_text = f"""
⚙️ <b>Настройки</b>

<b>Часовой пояс:</b> {user.timezone}
<b>Подписка на календарь:</b>
<code>{ical_url}</code>

Скопируй эту ссылку и добавь в свое календарное приложение (Google Calendar, Apple Calendar и т.д.)

<b>Внешний календарь:</b> {"✅ Подключен" if user.external_ical_url else "❌ Не подключен"}
    """
    
    await message.answer(settings_text)


@router.message(Command("calendar"))
async def cmd_calendar(message: Message, session: AsyncSession) -> None:
    """Handle /calendar command"""
    telegram_id = message.from_user.id
    
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Сначала используй /start для регистрации")
        return
    
    # TODO: Implement calendar view
    await message.answer("📅 Показ календаря - в разработке")


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """Handle voice messages"""
    await message.answer("🎤 Обработка голосового сообщения...")
    # TODO: Implement voice processing
    await message.answer("Функция в разработке. Пока используй текстовые сообщения.")


@router.message(F.text)
async def handle_text(message: Message, session: AsyncSession) -> None:
    """Handle text messages"""
    telegram_id = message.from_user.id
    
    # Check if user exists
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Сначала используй /start для регистрации")
        return
    
    # TODO: Process with LLM
    await message.answer(
        f"Получил твое сообщение: '{message.text}'\n\n"
        "Обработка через AI - в разработке."
    )