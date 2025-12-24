"""
Роуты для работы с Google Calendar API
С JWT аутентификацией через Bearer токены
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status

from .service import get_calendar_service
from ..schemas import (
    EventCreate, EventUpdate, EventResponse, 
    FreeSlotRequest, FreeSlotResponse, SuccessResponse,
    CalendarSummaryResponse, ErrorResponse
)
from ..database import get_db
from ..auth.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

calendar_router = APIRouter(prefix="/calendar", tags=["Календарь"])

# =========== ПОЛУЧЕНИЕ СОБЫТИЙ ===========

@calendar_router.get(
    "/events", 
    response_model=List[EventResponse],
    summary="Получить события пользователя",
    description="Возвращает список событий из календаря пользователя. "
                "Требует Bearer токен в заголовке Authorization."
)
async def get_user_events(
    max_results: int = Query(10, ge=1, le=100, description="Максимальное количество событий"),
    time_min: Optional[str] = Query(None, description="Начальная дата/время в ISO формате"),
    time_max: Optional[str] = Query(None, description="Конечная дата/время в ISO формате"),
    # Для обратной совместимости (deprecated)
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Получить события пользователя из календаря"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        
        events = await calendar_service.get_events(
            max_results=max_results,
            time_min=time_min,
            time_max=time_max
        )
        
        return events
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "аутентификац" in error_msg.lower() or "authenticat" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется авторизация в Google Calendar. Сначала используйте /auth/login"
            )
        elif "не найден" in error_msg.lower() or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при получении событий: {error_msg}"
            )

# =========== ПОЛУЧЕНИЕ КОНКРЕТНОГО СОБЫТИЯ ===========

@calendar_router.get(
    "/events/{event_id}", 
    response_model=EventResponse,
    summary="Получить конкретное событие",
    description="Возвращает информацию о конкретном событии по его ID"
)
async def get_user_event(
    event_id: str,
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Получить конкретное событие пользователя по ID"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        event = await calendar_service.get_event(event_id)
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "не найден" in error_msg.lower() or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Событие {event_id} не найдено"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при получении события: {error_msg}"
            )

# =========== СОЗДАНИЕ СОБЫТИЯ ===========

@calendar_router.post(
    "/events", 
    response_model=EventResponse,
    summary="Создать новое событие",
    description="Создает новое событие в календаре пользователя"
)
async def create_user_event(
    event: EventCreate,
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Создать новое событие в календаре пользователя"""
    try:
        user_id = current_user["telegram_id"]
        
        # Валидация времени
        _validate_event_times(event.start_time, event.end_time)
        
        calendar_service = get_calendar_service(user_id, session)
        
        created_event = await calendar_service.create_event(
            summary=event.summary,
            start_time=event.start_time,
            end_time=event.end_time,
            description=event.description or "",
            location=event.location or "",
            attendees=event.attendees or [],
            timezone=event.timezone
        )
        
        return created_event
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "аутентификац" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется авторизация в Google Calendar"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при создании события: {error_msg}"
            )

# =========== ОБНОВЛЕНИЕ СОБЫТИЯ ===========

@calendar_router.put(
    "/events/{event_id}", 
    response_model=EventResponse,
    summary="Обновить событие",
    description="Обновляет существующее событие пользователя"
)
async def update_user_event(
    event_id: str,
    updates: EventUpdate,
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Обновить существующее событие пользователя"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        
        # Проверяем, что событие существует
        await calendar_service.get_event(event_id)
        
        # Валидация времени, если передано
        if updates.start_time or updates.end_time:
            current_event = await calendar_service.get_event(event_id)
            start_time = updates.start_time or current_event['start']
            end_time = updates.end_time or current_event['end']
            _validate_event_times(start_time, end_time)
        
        updated_event = await calendar_service.update_event(
            event_id=event_id,
            summary=updates.summary,
            description=updates.description,
            start_time=updates.start_time,
            end_time=updates.end_time,
            location=updates.location
        )
        
        return updated_event
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "не найден" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Событие {event_id} не найдено"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при обновлении события: {error_msg}"
            )

# =========== УДАЛЕНИЕ СОБЫТИЯ ===========

@calendar_router.delete(
    "/events/{event_id}", 
    response_model=SuccessResponse,
    summary="Удалить событие",
    description="Удаляет событие из календаря пользователя"
)
async def delete_user_event(
    event_id: str,
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Удалить событие пользователя"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        
        success = await calendar_service.delete_event(event_id)
        if success:
            return SuccessResponse(message=f"Событие {event_id} успешно удалено")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось удалить событие"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "не найден" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Событие {event_id} не найдено"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при удалении события: {error_msg}"
            )

# =========== ПОИСК СВОБОДНЫХ СЛОТОВ ===========

@calendar_router.post(
    "/free-slots", 
    response_model=List[FreeSlotResponse],
    summary="Найти свободные слоты",
    description="Находит свободные промежутки времени на указанную дату"
)
async def find_user_free_slots(
    request: FreeSlotRequest,
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Найти свободные слоты пользователя"""
    try:
        user_id = current_user["telegram_id"]
        
        # Валидация даты
        _validate_date(request.date)
        
        # Валидация параметров
        _validate_slot_parameters(
            request.start_hour, 
            request.end_hour, 
            request.duration_minutes
        )
        
        calendar_service = get_calendar_service(user_id, session)
        
        slots = await calendar_service.find_free_slots(
            date=request.date,
            duration_minutes=request.duration_minutes,
            start_hour=request.start_hour,
            end_hour=request.end_hour
        )
        
        return slots
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "аутентификац" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется авторизация в Google Calendar"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при поиске свободных слотов: {error_msg}"
            )

# =========== ПОИСК СОБЫТИЙ ПО ТЕКСТУ ===========

@calendar_router.get(
    "/search", 
    response_model=List[EventResponse],
    summary="Поиск событий",
    description="Поиск событий пользователя по тексту"
)
async def search_user_events(
    query: str = Query(..., min_length=1, max_length=100, description="Текст для поиска"),
    max_results: int = Query(20, ge=1, le=50, description="Максимальное количество результатов"),
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Поиск событий пользователя по тексту"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        
        events = await calendar_service.search_events(
            query=query, 
            max_results=max_results
        )
        
        return events
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при поиске событий: {str(e)}"
        )

# =========== БЛИЖАЙШИЕ СОБЫТИЯ ===========

@calendar_router.get(
    "/upcoming", 
    response_model=List[EventResponse],
    summary="Ближайшие события",
    description="Получить ближайшие события пользователя"
)
async def get_user_upcoming_events(
    hours: int = Query(24, ge=1, le=168, description="Количество часов вперед для поиска"),
    max_results: int = Query(10, ge=1, le=50, description="Максимальное количество событий"),
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Получить ближайшие события пользователя"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        
        events = await calendar_service.get_upcoming_events(
            hours=hours, 
            max_results=max_results
        )
        
        return events
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении ближайших событий: {str(e)}"
        )

# =========== СТАТИСТИКА КАЛЕНДАРЯ ===========

@calendar_router.get(
    "/summary",
    response_model=CalendarSummaryResponse,
    summary="Статистика календаря",
    description="Краткая статистика по календарю пользователя"
)
async def get_calendar_summary(
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Получить статистику по календарю пользователя"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        
        summary = await calendar_service.get_calendar_summary()
        
        return CalendarSummaryResponse(
            today_events_count=summary['today_events_count'],
            tomorrow_events_count=summary['tomorrow_events_count'],
            next_24h_events_count=summary['next_24h_events_count'],
            next_event=summary['next_event']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статистики: {str(e)}"
        )

# =========== СТАТУС ПОДКЛЮЧЕНИЯ ===========

@calendar_router.get(
    "/status",
    response_model=dict,
    summary="Статус подключения",
    description="Проверка подключения к Google Calendar"
)
async def check_calendar_status(
    # Для обратной совместимости
    tg_id: Optional[str] = Query(None, include_in_schema=False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Проверка статуса подключения к календарю"""
    try:
        user_id = current_user["telegram_id"]
        
        calendar_service = get_calendar_service(user_id, session)
        
        # Пробуем получить события (простая проверка)
        events = await calendar_service.get_events(max_results=1)
        
        return {
            "status": "connected",
            "user_id": user_id,
            "auth_method": current_user.get("auth_method", "unknown"),
            "has_access": True,
            "events_available": len(events) > 0,
            "message": "Успешно подключено к Google Calendar"
        }
        
    except Exception as e:
        error_msg = str(e)
        if "аутентификац" in error_msg.lower():
            return {
                "status": "unauthorized",
                "user_id": current_user.get("telegram_id", "unknown"),
                "has_access": False,
                "message": "Требуется авторизация в Google Calendar"
            }
        else:
            return {
                "status": "error",
                "user_id": current_user.get("telegram_id", "unknown"),
                "has_access": False,
                "error": error_msg
            }

# =========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===========

def _validate_event_times(start_time: str, end_time: str):
    """Валидация времени события"""
    try:
        # Проверяем, что время окончания позже времени начала
        if 'T' in start_time and 'T' in end_time:
            # Это время с датой
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            if end_dt <= start_dt:
                raise ValueError("Время окончания должно быть позже времени начала")
                
        elif 'T' not in start_time and 'T' not in end_time:
            # Это только дата
            start_date = datetime.strptime(start_time, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_time, "%Y-%m-%d").date()
            
            if end_date < start_date:
                raise ValueError("Дата окончания должна быть позже или равна дате начала")
                
        else:
            raise ValueError("Формат времени начала и окончания должен совпадать")
            
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError("Неверный формат времени. Используйте YYYY-MM-DD или YYYY-MM-DDTHH:MM:SS")
        raise

def _validate_date(date_str: str):
    """Валидация формата даты"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Неверный формат даты. Используйте YYYY-MM-DD")

def _validate_slot_parameters(start_hour: int, end_hour: int, duration_minutes: int):
    """Валидация параметров поиска слотов"""
    if not (0 <= start_hour <= 23):
        raise ValueError("start_hour должен быть от 0 до 23")
    if not (0 <= end_hour <= 23):
        raise ValueError("end_hour должен быть от 0 до 23")
    if start_hour >= end_hour:
        raise ValueError("start_hour должен быть меньше end_hour")
    if duration_minutes <= 0 or duration_minutes > 1440:
        raise ValueError("duration_minutes должен быть от 1 до 1440 (24 часа)")