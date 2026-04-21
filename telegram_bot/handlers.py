"""Обработчики команд для Telegram бота"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

try:
    from .api_client import APIClient
    from .config import BACKEND_API_URL
except ImportError:
    # Для запуска напрямую
    from api_client import APIClient
    from config import BACKEND_API_URL


# Хранилище токенов пользователей (в продакшене лучше использовать БД)
user_tokens: Dict[str, str] = {}


def get_user_token(user_id: str) -> Optional[str]:
    """Получить токен пользователя"""
    return user_tokens.get(str(user_id))


def save_user_token(user_id: str, token: str):
    """Сохранить токен пользователя"""
    user_tokens[str(user_id)] = token


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start (с поддержкой deep link)"""
    user = update.effective_user
    user_id = str(user.id)
    
    # Проверяем, есть ли параметр в deep link
    deep_link_param = None
    if context.args:
        deep_link_param = context.args[0]
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Это бот для тестирования AI Planner Backend API.

🔐 *Авторизация:*
Используйте команду /login для авторизации через Google Calendar.

📋 *Доступные команды:*
/login - Авторизоваться через Google
/check - Проверить статус авторизации
/events - Получить события календаря
/upcoming - Ближайшие события
/summary - Статистика календаря
/status - Статус подключения к календарю
/create_event - Создать новое событие
/search - Поиск событий
/free_slots - Найти свободные слоты
/help - Показать справку

💡 *Deep Link:*
Вы можете использовать deep link для авторизации:
`https://t.me/YOUR_BOT_USERNAME?start=AUTH_CODE`
"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /login - начало авторизации"""
    user = update.effective_user
    user_id = str(user.id)
    
    # Формируем URL для авторизации
    login_url = f"{BACKEND_API_URL}/auth/login?tg_id={user_id}"
    
    # Проверяем, является ли URL публичным (https) или localhost
    is_public_url = login_url.startswith("https://")
    
    if is_public_url:
        # Для публичных URL используем кнопку
        keyboard = [
            [InlineKeyboardButton("🔐 Авторизоваться через Google", url=login_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🔐 *Авторизация через Google Calendar*

Нажмите на кнопку ниже, чтобы начать авторизацию через Google.

После успешной авторизации вернитесь в бот и используйте команду /check для проверки статуса.
"""
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Для localhost отправляем ссылку в тексте
        # Используем более простое форматирование без сложной Markdown разметки
        text = f"""
🔐 *Авторизация через Google Calendar*

Для авторизации скопируйте и откройте эту ссылку в браузере:

{login_url}

📋 *Инструкция:*
1. Откройте ссылку в браузере
2. Авторизуйтесь через Google
3. Вернитесь в бот
4. Используйте команду /check для проверки статуса
"""
        # Отправляем без parse_mode или с 'HTML', если нужно форматирование
        await update.message.reply_text(text, parse_mode=None, disable_web_page_preview=False)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /check - проверка статуса авторизации"""
    user = update.effective_user
    user_id = str(user.id)
    
    api_client = APIClient()
    
    try:
        status = await api_client.get_auth_status(user_id)
        
        if status.get("authenticated") and status.get("ready"):
            jwt_token = status.get("jwt_token")
            if jwt_token:
                save_user_token(user_id, jwt_token)
            
            user_info = status.get("user_info", {})
            text = f"""
✅ *Авторизация успешна!*

📧 Email: `{user_info.get('google_email', 'N/A')}`
🆔 Google User ID: `{user_info.get('google_user_id', 'N/A')}`

Теперь вы можете использовать команды для работы с календарем!
"""
        else:
            text = f"""
❌ *Авторизация не завершена*

{status.get('message', 'Используйте /login для авторизации')}
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /events - получить события"""
    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "❌ Вы не авторизованы. Используйте /login для авторизации.",
            parse_mode=None
        )
        return
    
    api_client = APIClient()
    
    try:
        # Парсим параметры (если есть)
        max_results = 10
        if context.args:
            try:
                max_results = int(context.args[0])
            except:
                pass
        
        events = await api_client.get_events(token, max_results=max_results)
        
        if not events:
            await update.message.reply_text("📅 Событий не найдено.", parse_mode=None)
            return
        
        text = f"📅 *События календаря* (найдено: {len(events)})\n\n"
        
        for i, event in enumerate(events[:10], 1):
            summary = event.get('summary', 'Без названия')
            start = event.get('start', 'N/A')
            end = event.get('end', 'N/A')
            event_id = event.get('id', 'N/A')
            
            text += f"{i}. *{summary}*\n"
            text += f"   🕐 {start} - {end}\n"
            text += f"   🆔 `{event_id}`\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def upcoming_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /upcoming - ближайшие события"""
    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "❌ Вы не авторизованы. Используйте /login для авторизации.",
            parse_mode=None
        )
        return
    
    api_client = APIClient()
    
    try:
        hours = 24
        max_results = 10
        
        if context.args:
            try:
                hours = int(context.args[0])
            except:
                pass
        
        events = await api_client.get_upcoming_events(token, hours=hours, max_results=max_results)
        
        if not events:
            await update.message.reply_text(f"📅 Ближайших событий в следующие {hours} часов не найдено.", parse_mode=None)
            return
        
        text = f"📅 *Ближайшие события* (следующие {hours} часов)\n\n"
        
        for i, event in enumerate(events, 1):
            summary = event.get('summary', 'Без названия')
            start = event.get('start', 'N/A')
            end = event.get('end', 'N/A')
            
            text += f"{i}. *{summary}*\n"
            text += f"   🕐 {start} - {end}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /summary - статистика календаря"""
    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "❌ Вы не авторизованы. Используйте /login для авторизации.",
            parse_mode=None
        )
        return
    
    api_client = APIClient()
    
    try:
        summary = await api_client.get_calendar_summary(token)
        
        text = "📊 *Статистика календаря*\n\n"
        text += f"📅 Сегодня: {summary.get('today_events_count', 0)} событий\n"
        text += f"📅 Завтра: {summary.get('tomorrow_events_count', 0)} событий\n"
        text += f"📅 Следующие 24 часа: {summary.get('next_24h_events_count', 0)} событий\n"
        
        next_event = summary.get('next_event')
        if next_event:
            text += f"\n🎯 *Ближайшее событие:*\n"
            text += f"   {next_event.get('summary', 'N/A')}\n"
            text += f"   🕐 {next_event.get('start', 'N/A')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status - статус подключения"""
    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "❌ Вы не авторизованы. Используйте /login для авторизации.",
            parse_mode=None
        )
        return
    
    api_client = APIClient()
    
    try:
        status = await api_client.get_calendar_status(token)
        
        status_text = status.get('status', 'unknown')
        message = status.get('message', 'N/A')
        
        if status_text == 'connected':
            text = f"✅ *Статус подключения:* {status_text}\n\n{message}"
        else:
            text = f"❌ *Статус подключения:* {status_text}\n\n{message}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def create_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /create_event - создать событие"""
    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "❌ Вы не авторизованы. Используйте /login для авторизации.",
            parse_mode=None
        )
        return
    
    if not context.args or len(context.args) < 3:
        help_text = """
📝 *Создание события*

Использование: `/create_event <название> <дата_начала> <дата_окончания> [описание]`

Пример:
`/create_event Встреча 2024-01-20T14:00:00 2024-01-20T15:00:00 Описание встречи`

Формат даты: `YYYY-MM-DDTHH:MM:SS` (например: 2024-01-20T14:00:00)
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
        return
    
    api_client = APIClient()
    
    try:
        summary = context.args[0]
        start_time = context.args[1]
        end_time = context.args[2]
        description = ' '.join(context.args[3:]) if len(context.args) > 3 else None
        
        event = await api_client.create_event(
            token=token,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description
        )
        
        text = f"""
✅ *Событие создано!*

📝 Название: {event.get('summary', 'N/A')}
🕐 Начало: {event.get('start', 'N/A')}
🕐 Окончание: {event.get('end', 'N/A')}
🆔 ID: `{event.get('id', 'N/A')}`
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /search - поиск событий"""
    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "❌ Вы не авторизованы. Используйте /login для авторизации.",
            parse_mode=None
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите текст для поиска.\nПример: `/search встреча`", 
            parse_mode='Markdown'
        )
        return
    
    api_client = APIClient()
    
    try:
        query = ' '.join(context.args)
        events = await api_client.search_events(token, query)
        
        if not events:
            await update.message.reply_text(f"🔍 По запросу '{query}' ничего не найдено.", parse_mode=None)
            return
        
        text = f"🔍 *Результаты поиска* (найдено: {len(events)})\n\n"
        
        for i, event in enumerate(events[:10], 1):
            summary = event.get('summary', 'Без названия')
            start = event.get('start', 'N/A')
            end = event.get('end', 'N/A')
            
            text += f"{i}. *{summary}*\n"
            text += f"   🕐 {start} - {end}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def free_slots_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /free_slots - найти свободные слоты"""
    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)
    
    if not token:
        await update.message.reply_text(
            "❌ Вы не авторизованы. Используйте /login для авторизации.",
            parse_mode=None
        )
        return
    
    if not context.args:
        # Используем сегодняшнюю дату по умолчанию
        today = datetime.now().strftime("%Y-%m-%d")
        date = today
        duration = 60
    else:
        date = context.args[0]
        duration = int(context.args[1]) if len(context.args) > 1 else 60
    
    api_client = APIClient()
    
    try:
        slots = await api_client.find_free_slots(
            token=token,
            date=date,
            duration_minutes=duration
        )
        
        if not slots:
            await update.message.reply_text(f"❌ Свободных слотов на {date} не найдено.", parse_mode=None)
            return
        
        text = f"🕐 *Свободные слоты* на {date} (длительность: {duration} мин)\n\n"
        
        for i, slot in enumerate(slots[:10], 1):
            start = slot.get('start', 'N/A')
            end = slot.get('end', 'N/A')
            text += f"{i}. {start} - {end}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", parse_mode=None)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help - справка"""
    text = """
📚 *Справка по командам*

🔐 *Авторизация:*
/login - Начать авторизацию через Google Calendar
/check - Проверить статус авторизации

📅 *Работа с событиями:*
/events [количество] - Получить события (по умолчанию 10)
/upcoming [часы] - Ближайшие события (по умолчанию 24 часа)
/summary - Статистика календаря
/status - Статус подключения к календарю

➕ *Создание и поиск:*
/create_event <название> <начало> <окончание> [описание]
   Пример: /create_event Встреча 2024-01-20T14:00:00 2024-01-20T15:00:00
/search <текст> - Поиск событий по тексту
/free_slots [дата] [длительность_мин] - Найти свободные слоты

💡 *Примеры:*
/events 5 - Получить 5 событий
/upcoming 48 - События на следующие 48 часов
/search встреча - Найти события со словом "встреча"
/free_slots 2024-01-20 30 - Свободные слоты на 30 минут

Для получения помощи используйте /help
"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

def format_agent_response(data: dict) -> str:
    if data.get("type") == "text":
        return data.get("content", "Пустой ответ")

    if data.get("type") == "tool_result":
        lines = ["✅ Выполнено:\n"]
        for item in data.get("results", []):
            tool = item.get("tool")
            output = item.get("output")

            lines.append(f"🔧 {tool}")
            if isinstance(output, list):
                lines.append(f"• Найдено: {len(output)}")
            elif isinstance(output, dict):
                summary = output.get("summary")
                if summary:
                    lines.append(f"• {summary}")
                else:
                    lines.append(f"• OK")
            lines.append("")

        return "\n".join(lines)

    return "Неизвестный ответ от сервера"

async def prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Напиши запрос после команды.\n\n"
            "Пример:\n"
            "/prompt создай встречу завтра в 18:00"
        )
        return

    prompt_text = " ".join(context.args)

    user_id = str(update.effective_user.id)
    token = get_user_token(user_id)

    if not token:
        await update.message.reply_text(
            "Сначала нужно авторизоваться: /login"
        )
        return

    api = APIClient()

    try:
        response = await api.send_agent_prompt(
            token=token,
            prompt=prompt_text,
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")
        return

    await update.message.reply_text(
        format_agent_response(response),
        disable_web_page_preview=True,
    )