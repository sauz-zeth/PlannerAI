import json
from typing import Any, Dict, List

from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from .tools import calendar_tools
from ..calendar.service import get_calendar_service


# ================== LLM CLIENT ==================

client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio",
)

MODEL_NAME = "qwen/qwen3-4b-2507"


# ================== SYSTEM PROMPT ==================

from datetime import datetime, timedelta


def _build_system_prompt() -> str:
    """Строит системный промпт с актуальной датой на момент запроса."""
    now = datetime.now()
    today = now.date()

    WEEKDAYS_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    today_name = WEEKDAYS_RU[today.weekday()]

    # Таблица ближайших 14 дней с названиями
    day_lines = []
    for i in range(1, 15):
        d = today + timedelta(days=i)
        name = WEEKDAYS_RU[d.weekday()]
        label = ""
        if i == 1:
            label = " (завтра)"
        elif i == 2:
            label = " (послезавтра)"
        day_lines.append(f"  {name}: {d.isoformat()}{label}")
    days_table = "\n".join(day_lines)

    return f"""Ты агент для управления календарём пользователя.

Сегодня: {today.isoformat()} ({today_name})

Ближайшие даты (используй ТОЛЬКО эти значения, не вычисляй сам):
{days_table}

Правила:
1. Если запрос связан с календарём — ОБЯЗАТЕЛЬНО вызывай функцию.
2. Не выдумывай данные.
3. Не отвечай обычным текстом, если можно вызвать tool.
4. Все даты передавай в формате YYYY-MM-DDTHH:MM:SSZ (UTC = московское время для этого проекта).
5. Если время не указано — используй 19:00.
6. Длительность события — 2 часа по умолчанию, если не указано иное.

Выбор инструмента — создание vs поиск свободного времени:
- create_event: когда пользователь хочет добавить/запланировать/создать дело или событие.
  Фразы-триггеры: "хочу", "нужно", "надо", "планирую", "собираюсь", "добавь", "создай", "запланируй", "поставь", "занеси", "напомни", "мне нужно".
  Фраза "прежде чем X", "до X", "перед X" означает только время события — НЕ повод искать слоты.
  Примеры:
    "хочу завтра на свидание" → create_event(summary="Свидание", start=завтра19:00, end=завтра21:00)
    "мне нужно завтра купить молоко" → create_event(summary="Купить молоко", start=завтра19:00, end=завтра21:00)
    "надо в пятницу позвонить врачу" → create_event(summary="Позвонить врачу", start=пятница19:00, ...)
    "мне нужно купить молоко прежде чем купить справку" → create_event(summary="Купить молоко", start=завтра19:00, ...)
- find_free_slots: ТОЛЬКО если пользователь ЯВНО спрашивает про свободное время.
  Фразы-триггеры: "когда я свободен", "найди свободное время", "есть ли окно", "свободные слоты".
  НИКОГДА не вызывать find_free_slots когда пользователь описывает задачу или дело!

Выбор инструмента для просмотра событий:
- get_upcoming_events: когда пользователь спрашивает "ближайшие события" без конкретного периода (hours=168).
- get_events с time_min + time_max: когда называет конкретный день или период:
  * "сегодня" → {today.isoformat()}T00:00:00Z .. {today.isoformat()}T23:59:59Z
  * "завтра" → {(today + timedelta(days=1)).isoformat()}T00:00:00Z .. {(today + timedelta(days=1)).isoformat()}T23:59:59Z
  * "на этой неделе" → time_min=сегодня, time_max=сегодня+7 дней
  * "через неделю" → time_min=сегодня+7 дней, time_max=сегодня+14 дней
  * "в [месяц]" → time_min=начало месяца, time_max=конец месяца
"""


# ================== PUBLIC API ==================

async def handle_prompt(
    prompt: str,
    user_id: str,
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    Основная точка входа агента.
    Принимает prompt → LLM → tool calls → выполнение → ответ
    """

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        tools=calendar_tools,
        tool_choice="auto",
    )

    message = completion.choices[0].message

    # Если LLM решил ответить текстом (редко, но возможно)
    if not message.tool_calls:
        return {
            "type": "text",
            "content": message.content or "Нет ответа",
        }

    # Исполняем tool calls
    tool_results = await _execute_tool_calls(
        tool_calls=message.tool_calls,
        user_id=user_id,
        session=session,
    )

    # Генерируем понятный ответ на основе результатов
    content = await _generate_quick_response(
        original_prompt=prompt,
        tool_results=tool_results,
    )

    return {
        "type": "text",
        "content": content,
    }


# ================== TOOL EXECUTION ==================

async def _execute_tool_calls(
    tool_calls: List[Any],
    user_id: str,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    Выполняет tool calls, выбранные LLM
    """

    calendar_service = get_calendar_service(user_id, session)

    results: List[Dict[str, Any]] = []

    for call in tool_calls:
        tool_name = call.function.name
        arguments = _safe_json_load(call.function.arguments)
        
        # Логируем аргументы для отладки
        print(f"🔍 TOOL CALL: {tool_name}")
        print(f"🔍 ARGUMENTS: {arguments}")
        
        if tool_name == "get_events":
            data = await calendar_service.get_events(
                max_results=arguments.get("max_results", 10),
                time_min=arguments.get("time_min"),
                time_max=arguments.get("time_max"),
            )

        elif tool_name == "create_event":
            # Проверяем обязательные поля
            required_fields = ["summary", "start_time", "end_time"]
            missing_fields = [field for field in required_fields if field not in arguments]
            
            if missing_fields:
                data = {"error": f"Отсутствуют обязательные поля: {missing_fields}"}
            else:
                # Логируем данные события
                print(f"📅 СОЗДАНИЕ СОБЫТИЯ:")
                print(f"   Название: {arguments.get('summary')}")
                print(f"   Начало: {arguments.get('start_time')}")
                print(f"   Конец: {arguments.get('end_time')}")
                print(f"   Описание: {arguments.get('description', '')}")
                print(f"   Место: {arguments.get('location', '')}")
                
                data = await calendar_service.create_event(
                    summary=arguments["summary"],
                    start_time=arguments["start_time"],
                    end_time=arguments["end_time"],
                    description=arguments.get("description", ""),
                    location=arguments.get("location", ""),
                )


        elif tool_name == "update_event":
            data = await calendar_service.update_event(
                event_id=arguments["event_id"],
                summary=arguments.get("summary"),
                description=arguments.get("description"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                location=arguments.get("location"),
            )

        elif tool_name == "delete_event":
            data = await calendar_service.delete_event(
                event_id=arguments["event_id"]
            )

        elif tool_name == "find_free_slots":
            data = await calendar_service.find_free_slots(
                date=arguments["date"],
                duration_minutes=arguments.get("duration_minutes", 60),
                start_hour=arguments.get("start_hour", 9),
                end_hour=arguments.get("end_hour", 18),
            )

        elif tool_name == "search_events":
            data = await calendar_service.search_events(
                query=arguments["query"],
                max_results=arguments.get("max_results", 20),
            )

        elif tool_name == "get_upcoming_events":
            data = await calendar_service.get_upcoming_events(
                hours=arguments.get("hours", 24),
                max_results=arguments.get("max_results", 10),
            )

        elif tool_name == "get_calendar_summary":
            data = await calendar_service.get_calendar_summary()

        else:
            data = {"error": f"Unknown tool: {tool_name}"}

        results.append(
            {
                "tool": tool_name,
                "arguments": arguments,
                "output": data,
            }
        )

    return results


# ================== RESPONSE GENERATION ==================

async def _generate_quick_response(
    original_prompt: str,
    tool_results: List[Dict[str, Any]],
) -> str:
    """
    Быстрая генерация ответа без второго вызова LLM
    """
    if not tool_results:
        return "Не удалось выполнить запрос."
    
    result = tool_results[0]
    tool_name = result["tool"]
    output = result["output"]
    
    if tool_name == "get_upcoming_events" and isinstance(output, list):
        if not output:
            return "🎯 На ближайшее время событий не найдено."

        MONTHS = ["января","февраля","марта","апреля","мая","июня",
                  "июля","августа","сентября","октября","ноября","декабря"]
        WEEKDAYS = ["пн","вт","ср","чт","пт","сб","вс"]

        def day_header(iso_start: str) -> str:
            try:
                from datetime import date as date_cls
                d_str = iso_start[:10]
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
                today = datetime.now().date()
                wd = WEEKDAYS[d.weekday()]
                if d == today:
                    return f"Сегодня, {d.day} {MONTHS[d.month-1]}, {wd}"
                if (d - today).days == 1:
                    return f"Завтра, {d.day} {MONTHS[d.month-1]}, {wd}"
                return f"{d.day} {MONTHS[d.month-1]}, {wd}"
            except Exception:
                return iso_start[:10]

        def fmt_time(event: dict) -> str:
            s = event.get("start", "")
            e = event.get("end", "")
            if "T" not in s:
                return "весь день"
            return f"{s[11:16]} – {e[11:16]}" if "T" in e else s[11:16]

        # Группируем по дате
        groups: Dict[str, list] = {}
        for ev in output:
            day = ev.get("start", "")[:10]
            groups.setdefault(day, []).append(ev)

        lines = []
        for day, evs in groups.items():
            lines.append(f"📅 {day_header(day)}")
            for ev in evs:
                t = fmt_time(ev)
                title = ev.get("summary", "Без названия")
                loc = ev.get("location", "")
                lines.append(f"  {t}  {title}")
                if loc:
                    lines.append(f"       📍 {loc}")
            lines.append("")

        return "\n".join(lines).rstrip()
    
    elif tool_name == "create_event" and isinstance(output, dict):
        summary = output.get('summary', 'Событие')
        start_time = output.get('readable_start', '')
        return f"✅ Событие создано: {summary}\n📅 {start_time}"
    
    elif tool_name == "get_events" and isinstance(output, list):
        if not output:
            return "📭 Событий за этот период не найдено."

        MONTHS = ["января","февраля","марта","апреля","мая","июня",
                  "июля","августа","сентября","октября","ноября","декабря"]
        WEEKDAYS = ["пн","вт","ср","чт","пт","сб","вс"]

        def day_header(iso_start: str) -> str:
            try:
                d = datetime.strptime(iso_start[:10], "%Y-%m-%d").date()
                today = datetime.now().date()
                wd = WEEKDAYS[d.weekday()]
                if d == today:
                    return f"Сегодня, {d.day} {MONTHS[d.month-1]}, {wd}"
                if (d - today).days == 1:
                    return f"Завтра, {d.day} {MONTHS[d.month-1]}, {wd}"
                return f"{d.day} {MONTHS[d.month-1]}, {wd}"
            except Exception:
                return iso_start[:10]

        def fmt_time(ev: dict) -> str:
            s = ev.get("start", "")
            e = ev.get("end", "")
            if "T" not in s:
                return "весь день"
            return f"{s[11:16]} – {e[11:16]}" if "T" in e else s[11:16]

        groups: Dict[str, list] = {}
        for ev in output:
            day = ev.get("start", "")[:10]
            groups.setdefault(day, []).append(ev)

        lines = []
        for day, evs in groups.items():
            lines.append(f"📅 {day_header(day)}")
            for ev in evs:
                t = fmt_time(ev)
                title = ev.get("summary", "Без названия")
                loc = ev.get("location", "")
                lines.append(f"  {t}  {title}")
                if loc:
                    lines.append(f"       📍 {loc}")
            lines.append("")

        return "\n".join(lines).rstrip()
    
    elif tool_name == "get_calendar_summary" and isinstance(output, dict):
        return (
            f"📊 Статистика календаря:\n"
            f"• Сегодня: {output.get('today_events_count', 0)} событий\n"
            f"• Завтра: {output.get('tomorrow_events_count', 0)} событий\n"
            f"• Следующие 24 часа: {output.get('next_24h_events_count', 0)} событий"
        )
    
    elif tool_name == "update_event" and isinstance(output, dict):
        title = output.get("summary", "Событие")
        start = output.get("readable_start") or output.get("start", "")
        return f"✅ Обновлено: <b>{title}</b>\n📅 {start}"

    elif tool_name == "delete_event":
        return "🗑️ Событие удалено."

    else:
        return f"✅ Готово."

# ================== UTILS ==================

def _safe_json_load(raw: str) -> Dict[str, Any]:
    """
    Безопасный json.loads с защитой от мусора от LLM
    """
    try:
        return json.loads(raw)
    except Exception:
        return {}