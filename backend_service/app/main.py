from fastapi import FastAPI

from backend_service.app.api.public.routers import public_router
from backend_service.app.api.events.routers import events_router
from app.caldav.routers import caldav_router

app = FastAPI(title="AI Planner Backend")

app.include_router(public_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(caldav_router)