from datetime import datetime, timedelta
import re
from typing import Dict, Any

def parse_schedule_text(text: str) -> Dict[str, Any]:
    """
    Парсинг текстовых запросов для AI-Planner
    Извлечение дат, времени и событий
    """
    text_lower = text.lower().strip()
    
    # Извлечение даты
    event_date = extract_date(text_lower)
    
    # Извлечение времени
    event_time = extract_time(text_lower)
    
    # Определение типа события
    event_type = classify_event_type(text_lower)
    
    # Создание заголовка
    title = create_event_title(text, event_type)
    
    return {
        "event_id": f"ai_planner_event_{int(datetime.now().timestamp())}",
        "event_type": event_type,
        "scheduled_time": combine_datetime(event_date, event_time),
        "title": title,
        "duration": 60,
        "priority": "medium",
        "original_text": text,
        "source": "AI-Planner NLP Parser"
    }

def extract_date(text: str) -> datetime:
    """Извлечение даты из текста для AI-Planner"""
    now = datetime.now()
    
    if "завтра" in text:
        return now + timedelta(days=1)
    elif "послезавтра" in text:
        return now + timedelta(days=2)
    elif "сегодня" in text:
        return now
    elif "понедельник" in text:
        days_ahead = (0 - now.weekday()) % 7
        return now + timedelta(days=days_ahead)
    elif "вторник" in text:
        days_ahead = (1 - now.weekday()) % 7
        return now + timedelta(days=days_ahead)
    
    return now + timedelta(days=1)

def extract_time(text: str) -> str:
    """Извлечение времени из текста для AI-Planner"""
    time_pattern = r'(\d{1,2})[:\s]?(\d{2})?\s*(утра|вечера|дня|ночи|am|pm)?'
    matches = re.findall(time_pattern, text)
    
    if matches:
        hour, minute, period = matches[0]
        hour = int(hour)
        minute = int(minute) if minute else 0
        
        if period in ['вечера', 'дня', 'pm'] and hour < 12:
            hour += 12
        elif period in ['утра', 'ночи', 'am'] and hour == 12:
            hour = 0
            
        return f"{hour:02d}:{minute:02d}"
    
    return "10:00"

def classify_event_type(text: str) -> str:
    """Классификация типа события для AI-Planner"""
    text_lower = text.lower()
    
    event_patterns = {
        "meeting": ["встреча", "совещание", "митинг"],
        "workout": ["тренировка", "спорт", "зал", "фитнес"],
        "meal": ["обед", "ужин", "завтрак", "еда"],
        "appointment": ["прием", "визит", "доктор"],
        "presentation": ["презентация", "доклад"],
        "shopping": ["покупки", "магазин"],
        "study": ["учеба", "курс", "урок"]
    }
    
    for event_type, keywords in event_patterns.items():
        if any(keyword in text_lower for keyword in keywords):
            return event_type
    
    return "task"

def create_event_title(original_text: str, event_type: str) -> str:
    """Создание заголовка события для AI-Planner"""
    type_titles = {
        "meeting": "Встреча AI-Planner",
        "workout": "Тренировка AI-Planner", 
        "meal": "Прием пищи AI-Planner",
        "appointment": "Встреча AI-Planner",
        "presentation": "Презентация AI-Planner",
        "shopping": "Покупки AI-Planner",
        "study": "Обучение AI-Planner",
        "task": "Задача AI-Planner"
    }
    
    base_title = type_titles.get(event_type, "Событие AI-Planner")
    simple_text = original_text[:50]
    
    return f"{base_title}: {simple_text}"

def combine_datetime(date: datetime, time_str: str) -> str:
    """Объединение даты и времени для AI-Planner"""
    hour, minute = map(int, time_str.split(':'))
    combined = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return combined.isoformat()