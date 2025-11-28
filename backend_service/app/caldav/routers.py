from fastapi import APIRouter, Response
from app.storage.memory_storage import get_events
from app.caldav.ics_builder import build_ics_calendar

caldav_router = APIRouter(tags=["caldav"])

@caldav_router.get("/calendar/{token}/feed.ics")
async def calendar_feed(token: str):
    """
    Возвращает календарь пользователя в виде .ics файла.
    iOS / macOS / Android используют этот endpoint для подписки.
    """
    events = get_events(token)
    ics_text = build_ics_calendar(token, events)

    return Response(
        content=ics_text,
        media_type="text/calendar"
    )

