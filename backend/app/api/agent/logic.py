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

from datetime import datetime

# Получаем текущую дату
current_date = datetime.now()
formatted_date = current_date.strftime("%Y-%m-%d")

SYSTEM_PROMPT = f"""
Ты агент для управления календарём пользователя.

Текущая дата: {formatted_date}

Правила:
1. Если запрос связан с календарём — ОБЯЗАТЕЛЬНО вызывай функцию.
2. Не выдумывай данные.
3. Не отвечай обычным текстом, если можно вызвать tool.
4. Все даты и время возвращай в ISO формате с часовым поясом Z: YYYY-MM-DDTHH:MM:SSZ
5. Для вычисления дат используй ТЕКУЩУЮ ДАТУ: {formatted_date}
6. "послезавтра" = текущая дата + 2 дня
7. "завтра" = текущая дата + 1 день
8. Если время не указано, используй 19:00
9. Длительность события — 2 часа по умолчанию, если не указано иное

Примеры для ТЕКУЩЕЙ ДАТЫ {formatted_date}:
- "создай событие кино послезавтра в 19:00" → 
  start_time: "2025-12-27T19:00:00Z" (текущая дата 2025-12-25 + 2 дня)
  end_time: "2025-12-27T21:00:00Z"
- "создай событие завтра в 15:00" → 
  start_time: "2025-12-26T15:00:00Z" (текущая дата 2025-12-25 + 1 день)
  end_time: "2025-12-26T17:00:00Z"

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
            {"role": "system", "content": SYSTEM_PROMPT},
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
        
        events_count = len(output)
        hours = result["arguments"].get("hours", 24)
        days = hours // 24 if hours > 24 else 1
        
        # Определяем период
        if days == 1:
            period = "ближайшие 24 часа"
        elif days < 7:
            period = f"ближайшие {days} дня"
        else:
            period = f"ближайшие {days} дней"
        
        response_lines = [f"📅 Ближайшие события ({period}):", ""]
        
        # Группируем события по дням
        events_by_day = {}
        for event in output:
            start_time = event.get('readable_start', '')
            summary = event.get('summary', 'Без названия')
            time_to_event = event.get('time_to_event', '')
            
            # Извлекаем день из readable_start
            if "Завтра" in start_time:
                day_key = "Завтра"
            elif "Сегодня" in start_time:
                day_key = "Сегодня"
            else:
                # Пытаемся извлечь дату
                day_key = start_time.split()[0] if start_time else "Неизвестно"
            
            if day_key not in events_by_day:
                events_by_day[day_key] = []
            
            events_by_day[day_key].append({
                'summary': summary,
                'time': start_time,
                'time_to_event': time_to_event,
                'duration': event.get('duration', ''),
                'location': event.get('location', ''),
            })
        
        # Формируем ответ по дням
        for day, day_events in events_by_day.items():
            response_lines.append(f"{day}:")
            for i, event in enumerate(day_events, 1):
                line = f"  {i}. {event['summary']}"
                
                # Время события
                if event['time']:
                    # Извлекаем только время из формата "Завтра в 14:00"
                    time_part = event['time']
                    if ' в ' in time_part:
                        time_part = time_part.split(' в ')[1]
                    line += f" — {time_part}"
                
                # Дополнительная информация
                details = []
                if event['duration']:
                    details.append(f"{event['duration']}")
                if event['location']:
                    details.append(f"📍 {event['location']}")
                
                if details:
                    line += f" ({', '.join(details)})"
                
                response_lines.append(line)
            response_lines.append("")  # Пустая строка между днями
        
        response_lines.append(f"Всего найдено: {events_count} событий")
        
        return "\n".join(response_lines)
    
    elif tool_name == "create_event" and isinstance(output, dict):
        summary = output.get('summary', 'Событие')
        start_time = output.get('readable_start', '')
        return f"✅ Событие создано: {summary}\n📅 {start_time}"
    
    elif tool_name == "get_events" and isinstance(output, list):
        count = len(output)
        return f"📋 Найдено событий: {count}"
    
    elif tool_name == "get_calendar_summary" and isinstance(output, dict):
        return (
            f"📊 Статистика календаря:\n"
            f"• Сегодня: {output.get('today_events_count', 0)} событий\n"
            f"• Завтра: {output.get('tomorrow_events_count', 0)} событий\n"
            f"• Следующие 24 часа: {output.get('next_24h_events_count', 0)} событий"
        )
    
    else:
        # Общий ответ для других инструментов
        return f"✅ Операция выполнена: {tool_name}"

# ================== UTILS ==================

def _safe_json_load(raw: str) -> Dict[str, Any]:
    """
    Безопасный json.loads с защитой от мусора от LLM
    """
    try:
        return json.loads(raw)
    except Exception:
        return {}