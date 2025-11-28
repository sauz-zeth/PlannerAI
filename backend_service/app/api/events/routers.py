from fastapi import APIRouter, Query
from pydantic import BaseModel

events_router = APIRouter(tags=["events"])

from app.storage.memory_storage import add_event, get_events
from shared.schemas import EventCreate

@events_router.post("/events")
async def create_event(payload: EventCreate):
    """
    Создаёт новое событие в календаре (в памяти).
    Используется для тестов и для MVP логики.
    """
    event = add_event(
        token=payload.token,
        title=payload.title,
        start=payload.start,
        end=payload.end
    )
    return {"status": "ok", "event": event}

@events_router.get("/events")
async def list_events(token: str = Query(...)):
    """
    Получает все события пользователя.
    Не обязателен, но сильно помогает отладке.
    """
    return {"events": get_events(token)}