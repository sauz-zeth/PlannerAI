from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

"""
Pydantic схемы для всего проекта
"""

class AgentPublicRequest(BaseModel):
    text: str
    requested_at: datetime | None = None

class AgentPublicResponse(BaseModel):
    input_text: str
    result: str
    
# =========== Общие схемы ===========

class SuccessResponse(BaseModel):
    """Успешный ответ"""
    success: bool = True
    message: str = "Успешно"

class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    success: bool = False
    error: str

# =========== Аутентификация ===========

class AuthResponse(BaseModel):
    """Ответ с URL для авторизации"""
    auth_url: str

class TokenData(BaseModel):
    """Данные токенов пользователя"""
    access_token: str
    refresh_token: str
    expires_at: int
    google_user_id: str

# =========== Календарь - Запросы ===========

class EventCreate(BaseModel):
    """Создание события"""
    summary: str = Field(..., min_length=1, max_length=200, description="Название события")
    description: Optional[str] = Field(None, description="Описание события")
    start_time: str = Field(..., description="Время начала в ISO формате (2024-01-20T14:00:00)")
    end_time: str = Field(..., description="Время окончания в ISO формате (2024-01-20T15:00:00)")
    timezone: str = Field("Europe/Moscow", description="Часовой пояс")
    location: Optional[str] = Field(None, description="Место проведения")
    attendees: Optional[List[str]] = Field(None, description="Список email участников")

class EventUpdate(BaseModel):
    """Обновление события"""
    summary: Optional[str] = Field(None, min_length=1, max_length=200, description="Новое название события")
    description: Optional[str] = Field(None, description="Новое описание события")
    start_time: Optional[str] = Field(None, description="Новое время начала")
    end_time: Optional[str] = Field(None, description="Новое время окончания")
    location: Optional[str] = Field(None, description="Новое место проведения")

class FreeSlotRequest(BaseModel):
    """Запрос на поиск свободных слотов"""
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")
    duration_minutes: int = Field(60, ge=1, le=1440, description="Продолжительность слота в минутах")
    start_hour: int = Field(9, ge=0, le=23, description="Начальный час для поиска (0-23)")
    end_hour: int = Field(18, ge=0, le=23, description="Конечный час для поиска (0-23)")

# =========== Календарь - Ответы ===========

class AttendeeResponse(BaseModel):
    """Участник события"""
    email: str
    responseStatus: str

class EventResponse(BaseModel):
    """Ответ с информацией о событии"""
    id: str = Field(..., description="ID события")
    summary: str = Field(..., description="Название события")
    description: Optional[str] = Field(None, description="Описание события")
    location: Optional[str] = Field(None, description="Место проведения")
    start: str = Field(..., description="Время начала")
    end: str = Field(..., description="Время окончания")
    status: Optional[str] = Field(None, description="Статус события (confirmed, tentative, cancelled)")
    htmlLink: Optional[str] = Field(None, description="Ссылка на событие в Google Calendar")
    creator: Optional[str] = Field(None, description="Email создателя события")
    attendees: Optional[List[AttendeeResponse]] = Field(None, description="Участники события")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "event123",
                "summary": "Встреча с командой",
                "description": "Обсуждение проекта",
                "location": "Офис",
                "start": "2024-01-20T14:00:00",
                "end": "2024-01-20T15:00:00",
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/event?id=event123",
                "creator": "user@example.com",
                "attendees": [
                    {"email": "participant1@example.com", "responseStatus": "accepted"}
                ]
            }
        }
    )

class FreeSlotResponse(BaseModel):
    """Свободный слот времени"""
    start: str = Field(..., description="Начало слота в ISO формате")
    end: str = Field(..., description="Конец слота в ISO формате")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start": "2024-01-20T09:00:00",
                "end": "2024-01-20T10:00:00"
            }
        }
    )

class CalendarSummaryResponse(BaseModel):
    """Статистика календаря"""
    today_events_count: int = Field(..., description="Количество событий сегодня")
    tomorrow_events_count: int = Field(..., description="Количество событий завтра")
    next_24h_events_count: int = Field(..., description="Количество событий в ближайшие 24 часа")
    next_event: Optional[EventResponse] = Field(None, description="Ближайшее событие")

# =========== AI/Чат ===========

class ChatRequest(BaseModel):
    """Запрос к AI ассистенту"""
    message: str = Field(..., min_length=1, max_length=1000, description="Сообщение пользователя")
    user_id: Optional[str] = Field(None, description="ID пользователя")

class ChatResponse(BaseModel):
    """Ответ от AI ассистента"""
    response: str = Field(..., description="Текстовый ответ")
    tool_used: Optional[str] = Field(None, description="Использованный инструмент")
    data: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")

# =========== Утилиты ===========

class CalendarStatusResponse(BaseModel):
    """Статус подключения к календарю"""
    status: str = Field(..., description="Статус (connected, unauthorized, error)")
    user_id: str = Field(..., description="ID пользователя")
    has_access: bool = Field(..., description="Есть ли доступ к календарю")
    message: str = Field(..., description="Сообщение о статусе")
    error: Optional[str] = Field(None, description="Ошибка (если есть)")

class SearchEventsRequest(BaseModel):
    """Поиск событий"""
    query: str = Field(..., min_length=1, max_length=100, description="Текст для поиска")
    max_results: int = Field(20, ge=1, le=50, description="Максимальное количество результатов")

# =========== Примеры для Swagger ===========

class ExampleResponses:
    """Примеры ответов для документации"""
    
    EVENT_RESPONSE = {
        "id": "abc123def456",
        "summary": "Еженедельное совещание",
        "description": "Обсуждение текущих задач",
        "location": "Конференц-зал",
        "start": "2024-01-22T10:00:00",
        "end": "2024-01-22T11:00:00",
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?eid=abc123",
        "creator": "me@example.com",
        "attendees": [
            {"email": "colleague@example.com", "responseStatus": "accepted"}
        ]
    }
    
    FREE_SLOTS_RESPONSE = [
        {"start": "2024-01-22T09:00:00", "end": "2024-01-22T10:00:00"},
        {"start": "2024-01-22T14:00:00", "end": "2024-01-22T15:00:00"}
    ]
    
    CALENDAR_SUMMARY = {
        "today_events_count": 3,
        "tomorrow_events_count": 2,
        "next_24h_events_count": 5,
        "next_event": EVENT_RESPONSE
    }