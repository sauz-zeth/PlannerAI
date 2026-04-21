"""Обработчики команд для Telegram бота"""
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes
from telegram.error import BadRequest

try:
    from .api_client import APIClient
    from .config import BACKEND_API_URL, OPENAI_API_KEY
except ImportError:
    from api_client import APIClient
    from config import BACKEND_API_URL, OPENAI_API_KEY


# ─────────────────────────────────────────────
# Хранилище токенов и главного сообщения
# ─────────────────────────────────────────────

user_tokens: Dict[str, str] = {}
main_message_ids: Dict[str, int] = {}   # user_id → message_id "окна"


def get_user_token(user_id: str) -> Optional[str]:
    return user_tokens.get(str(user_id))


def save_user_token(user_id: str, token: str):
    user_tokens[str(user_id)] = token


# ─────────────────────────────────────────────
# "Одно окно": edit или send+track
# ─────────────────────────────────────────────

async def _show(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: str,
    text: str,
    reply_markup=None,
    parse_mode: str = None,
    **kwargs,
) -> None:
    """Удаляет старое главное сообщение и отправляет новое снизу."""
    mid = main_message_ids.pop(user_id, None)
    if mid:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass

    msg: Message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        **kwargs,
    )
    main_message_ids[user_id] = msg.message_id


async def _update(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: str,
    text: str,
    reply_markup=None,
    parse_mode: str = None,
    **kwargs,
) -> None:
    """Редактирует текущее главное сообщение на месте (для loading → result)."""
    mid = main_message_ids.get(user_id)
    if mid:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=mid,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs,
            )
            return
        except BadRequest as e:
            if "Message is not modified" in str(e):
                return
        except Exception:
            pass
    # Фолбек — заменить
    await _show(context, chat_id, user_id, text, reply_markup=reply_markup,
                parse_mode=parse_mode, **kwargs)


async def _delete_user_message(update: Update) -> None:
    """Удаляет входящее сообщение пользователя (текст / голос / команду)."""
    try:
        await update.message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────
# Вспомогательные функции форматирования
# ─────────────────────────────────────────────

MONTHS   = ["января","февраля","марта","апреля","мая","июня",
            "июля","августа","сентября","октября","ноября","декабря"]
WEEKDAYS = ["пн","вт","ср","чт","пт","сб","вс"]


def _day_header(date_str: str) -> str:
    try:
        d     = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        today = datetime.now().date()
        wd    = WEEKDAYS[d.weekday()]
        if d == today:
            return f"Сегодня, {d.day} {MONTHS[d.month-1]}, {wd}"
        if (d - today).days == 1:
            return f"Завтра, {d.day} {MONTHS[d.month-1]}, {wd}"
        return f"{d.day} {MONTHS[d.month-1]}, {wd}"
    except Exception:
        return date_str[:10]


def _event_timerange(event: dict) -> str:
    s = event.get("start", "")
    e = event.get("end", "")
    if "T" not in s:
        return "весь день"
    return f"{s[11:16]} – {e[11:16]}" if "T" in e else s[11:16]


# ─────────────────────────────────────────────
# Главное меню
# ─────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Мои события",     callback_data="cmd_events")],
        [InlineKeyboardButton("➕ Добавить событие", callback_data="cmd_add")],
        [InlineKeyboardButton("💡 Что я умею",       callback_data="cmd_help")],
    ])


# ─────────────────────────────────────────────
# Авторизация
# ─────────────────────────────────────────────

async def _do_check_auth(user_id: str) -> dict:
    api = APIClient()
    status = await api.get_auth_status(user_id)
    if status.get("authenticated") and status.get("ready"):
        jwt = status.get("jwt_token")
        if jwt:
            save_user_token(user_id, jwt)
        return {"ok": True, "user_info": status.get("user_info", {})}
    return {"ok": False, "message": status.get("message", "Авторизация не завершена.")}


def _login_content(user_id: str) -> tuple[str, InlineKeyboardMarkup, dict]:
    """Возвращает (текст, клавиатура, kwargs) для экрана логина."""
    login_url = f"{BACKEND_API_URL}/auth/login?tg_id={user_id}"
    done_btn  = InlineKeyboardButton("✅ Я авторизовался", callback_data="check_auth")
    if login_url.startswith("https://"):
        return (
            "Нажми кнопку, войди через Google и вернись сюда:",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Войти через Google", url=login_url)],
                [done_btn],
            ]),
            {},
        )
    else:
        return (
            "Скопируй ссылку и открой в браузере:\n\n"
            f"<code>{login_url}</code>\n\n"
            "После авторизации нажми кнопку ниже:",
            InlineKeyboardMarkup([[done_btn]]),
            {"parse_mode": "HTML", "disable_web_page_preview": True},
        )


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    user_id = str(user.id)
    chat_id = update.effective_chat.id
    # Удаляем /start только если уже есть окно бота — иначе чат станет пустым
    # и Telegram снова покажет кнопку "Начать"
    if main_message_ids.get(user_id):
        await _delete_user_message(update)

    token = get_user_token(user_id)
    if token:
        await _show(
            context, chat_id, user_id,
            f"👋 Привет, {user.first_name}!\n\nВыбери действие или просто напиши запрос.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await _show(
            context, chat_id, user_id,
            f"👋 Привет, {user.first_name}!\n\n"
            "Я помогу управлять твоим Google Calendar.\n"
            "Можешь писать обычным текстом — например:\n"
            "<i>«создай встречу завтра в 15:00»</i>\n\n"
            "Для начала нужно войти через Google:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Войти через Google", callback_data="cmd_login")]
            ]),
            parse_mode="HTML",
        )


# ─────────────────────────────────────────────
# /login  /check  /events  /help
# ─────────────────────────────────────────────

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    text, kb, kwargs = _login_content(user_id)
    await _show(context, chat_id, user_id, text, reply_markup=kb, **kwargs)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    result = await _do_check_auth(user_id)
    if result["ok"]:
        info = result["user_info"]
        await _show(
            context, chat_id, user_id,
            f"✅ Подключён как <b>{info.get('google_email', '')}</b>.\n\n"
            "Выбери действие или напиши запрос:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await _show(
            context, chat_id, user_id,
            f"❌ {result['message']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Войти через Google", callback_data="cmd_login")]
            ]),
        )


async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    token = get_user_token(user_id)
    if not token:
        await _show(
            context, chat_id, user_id,
            "Сначала нужно войти в аккаунт Google.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Войти через Google", callback_data="cmd_login")]
            ]),
        )
        return
    n = int(context.args[0]) if context.args else 10
    text, kb = await _build_events(token, max_results=n)
    await _show(context, chat_id, user_id, text, parse_mode="HTML", reply_markup=kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    await _show(
        context, chat_id, user_id,
        "Просто напиши мне что сделать:\n\n"
        "<i>«покажи события на этой неделе»</i>\n"
        "<i>«создай встречу завтра в 14:00»</i>\n"
        "<i>«перенеси кино на пятницу»</i>\n"
        "<i>«удали тренировку»</i>\n\n"
        "Или используй кнопки меню.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


# ─────────────────────────────────────────────
# Список событий
# ─────────────────────────────────────────────

def _events_keyboard(events: list) -> list[list]:
    rows = []
    for ev in events:
        eid   = ev.get("id", "")
        title = ev.get("summary", "Без названия")[:20]
        rows.append([
            InlineKeyboardButton(f"✏️ {title}", callback_data=f"edit_{eid}"),
            InlineKeyboardButton("🗑️",          callback_data=f"del_{eid}"),
        ])
    rows.append([InlineKeyboardButton("← Назад", callback_data="menu")])
    return rows


async def _build_events(token: str, max_results: int = 10) -> tuple[str, InlineKeyboardMarkup]:
    api      = APIClient()
    now      = datetime.utcnow()
    time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = now.replace(year=now.year + 1).strftime("%Y-%m-%dT%H:%M:%SZ")
    events   = await api.get_events(token, max_results=max_results, time_min=time_min, time_max=time_max)

    back = InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu")]])

    if not events:
        return "📭 Предстоящих событий нет.", back

    groups: dict = defaultdict(list)
    for ev in events:
        groups[ev.get("start", "")[:10]].append(ev)

    lines = []
    for day, evs in groups.items():
        lines.append(f"<b>📅 {_day_header(day)}</b>")
        for ev in evs:
            t     = _event_timerange(ev)
            title = ev.get("summary", "Без названия")
            loc   = ev.get("location", "")
            lines.append(f"  {t}  {title}")
            if loc:
                lines.append(f"       📍 {loc}")
        lines.append("")

    return "\n".join(lines).rstrip(), InlineKeyboardMarkup(_events_keyboard(events))


# ─────────────────────────────────────────────
# Callback-кнопки
# ─────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data    = query.data

    # Синхронизируем: кнопка нажата на конкретном сообщении — оно и есть главное
    main_message_ids[user_id] = query.message.message_id

    # ── Авторизация ──────────────────────────
    if data == "check_auth":
        result = await _do_check_auth(user_id)
        if result["ok"]:
            info = result["user_info"]
            await query.edit_message_text(
                f"✅ Подключён как <b>{info.get('google_email', '')}</b>.\n\n"
                "Выбери действие или напиши запрос:",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"❌ Авторизация не завершена.\n{result['message']}\n\n"
                "Пройди по ссылке и попробуй снова.",
            )

    elif data == "cmd_login":
        text, kb, kwargs = _login_content(user_id)
        await query.edit_message_text(text, reply_markup=kb, **kwargs)

    # ── Главное меню ─────────────────────────
    elif data == "menu":
        await query.edit_message_text(
            "Выбери действие или напиши запрос:",
            reply_markup=main_menu_keyboard(),
        )

    # ── Список событий ───────────────────────
    elif data == "cmd_events":
        token = get_user_token(user_id)
        if not token:
            await query.edit_message_text("Сначала войди через Google: /login")
            return
        text, kb = await _build_events(token)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

    # ── Добавить ─────────────────────────────
    elif data == "cmd_add":
        context.user_data["intent"] = "create"
        await query.edit_message_text(
            "Напиши что добавить, например:\n"
            "<i>«встреча с Димой в пятницу в 11:00»</i>",
            parse_mode="HTML",
        )

    # ── Инструкция ───────────────────────────
    elif data == "cmd_help":
        text = (
            "💡 <b>Что я умею</b>\n\n"

            "📋 <b>Просмотр событий</b>\n"
            "• <i>Какие у меня события на этой неделе?</i>\n"
            "• <i>Что у меня завтра?</i>\n"
            "• <i>Покажи события на следующей неделе</i>\n"
            "• <i>Что запланировано в мае?</i>\n"
            "• <i>Есть ли у меня что-то в эту субботу?</i>\n\n"

            "➕ <b>Создание события</b>\n"
            "• <i>Создай встречу завтра в 15:00</i>\n"
            "• <i>Добавь тренировку в пятницу с 10:00 до 11:30</i>\n"
            "• <i>Запланируй звонок с Димой послезавтра в 12:00</i>\n"
            "• <i>Добавь событие Кино 25 апреля в 19:00</i>\n\n"

            "✏️ <b>Изменение события</b>\n"
            "• Нажми ✏️ рядом с событием в списке, затем напиши:\n"
            "  <i>«перенеси на завтра в 16:00»</i>\n"
            "  <i>«измени время на 18:00»</i>\n"
            "  <i>«переименуй в Встреча с командой»</i>\n\n"

            "🗑️ <b>Удаление события</b>\n"
            "• Нажми 🗑️ рядом с событием в списке\n"
            "• Или напиши: <i>«удали тренировку в пятницу»</i>\n\n"

            "💬 Просто пиши обычным текстом — я разберусь."
        )
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("← Назад", callback_data="menu")]
            ]),
        )

    # ── Удалить ──────────────────────────────
    elif data.startswith("del_"):
        event_id = data[4:]
        await query.edit_message_text(
            "Удалить это событие?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Да, удалить", callback_data=f"delok_{event_id}"),
                    InlineKeyboardButton("❌ Отмена",      callback_data="cmd_events"),
                ]
            ]),
        )

    elif data.startswith("delok_"):
        event_id = data[6:]
        token    = get_user_token(user_id)
        if not token:
            await query.edit_message_text("Сначала войди через Google: /login")
            return
        try:
            api = APIClient()
            await api.delete_event(token, event_id)
            await query.edit_message_text(
                "🗑️ Событие удалено.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("← К событиям", callback_data="cmd_events")]
                ]),
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")

    # ── Изменить ─────────────────────────────
    elif data.startswith("edit_"):
        event_id = data[5:]
        context.user_data["editing_event_id"] = event_id
        await query.edit_message_text(
            "Напиши что изменить, например:\n"
            "<i>«перенеси на завтра в 16:00»</i> или <i>«переименуй в Кино»</i>",
            parse_mode="HTML",
        )


# ─────────────────────────────────────────────
# Текстовые сообщения → агент
# ─────────────────────────────────────────────

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Голосовые сообщения → faster-whisper (локально) → агент."""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    token   = get_user_token(user_id)

    await _delete_user_message(update)

    if not token:
        await _show(
            context, chat_id, user_id,
            "Сначала нужно войти в аккаунт Google.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Войти через Google", callback_data="cmd_login")]
            ]),
        )
        return

    await _show(context, chat_id, user_id, "🎙️ Распознаю речь...")

    try:
        import asyncio
        import tempfile
        import os

        voice_file  = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        def transcribe():
            model = _get_whisper_model()
            segments, _ = model.transcribe(tmp_path, language="ru", beam_size=1)
            return " ".join(seg.text for seg in segments).strip()

        text = await asyncio.get_event_loop().run_in_executor(None, transcribe)
        os.unlink(tmp_path)

        if not text:
            await _update(context, chat_id, user_id, "❌ Не удалось распознать речь.",
                          reply_markup=main_menu_keyboard())
            return

        await _update(context, chat_id, user_id,
                      f"🎙️ <i>{text}</i>\n\n⏳", parse_mode="HTML")

        editing_id = context.user_data.pop("editing_event_id", None)
        intent     = context.user_data.pop("intent", None)
        if editing_id:
            prompt = f"Измени событие с id={editing_id}: {text}"
        elif intent == "create":
            prompt = f"Создай событие: {text}"
        else:
            prompt = text

        api      = APIClient()
        response = await api.send_agent_prompt(token=token, prompt=prompt)
        content  = response.get("content") if response.get("type") == "text" else str(response)

        await _update(
            context, chat_id, user_id,
            f"🎙️ <i>{text}</i>\n\n{content or 'Готово.'}",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )

    except Exception as e:
        await _update(context, chat_id, user_id, f"❌ Ошибка: {e}",
                      reply_markup=main_menu_keyboard())


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    token   = get_user_token(user_id)

    await _delete_user_message(update)

    if not token:
        await _show(
            context, chat_id, user_id,
            "Чтобы я мог помочь, сначала войди в аккаунт Google.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Войти через Google", callback_data="cmd_login")]
            ]),
        )
        return

    editing_id = context.user_data.pop("editing_event_id", None)
    intent     = context.user_data.pop("intent", None)
    prompt     = update.message.text

    if editing_id:
        prompt = f"Измени событие с id={editing_id}: {prompt}"
    elif intent == "create":
        prompt = f"Создай событие: {prompt}"

    await _show(context, chat_id, user_id, "⏳")

    api = APIClient()
    try:
        response = await api.send_agent_prompt(token=token, prompt=prompt)
        content  = response.get("content") if response.get("type") == "text" else str(response)
        await _update(
            context, chat_id, user_id,
            content or "Не удалось получить ответ.",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        await _update(context, chat_id, user_id, f"❌ Ошибка: {e}",
                      reply_markup=main_menu_keyboard())
