from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.public.routers import public_router
from app.api.agent.routes import agent_router 
from app.api.auth.routes import auth_router
from app.api.calendar.routes import calendar_router
from app.api.database import init_db
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте приложения"""
    await init_db()
    yield


app = FastAPI(title="AI Planner Backend", lifespan=lifespan)
app.include_router(auth_router, prefix="/auth")
app.include_router(public_router, prefix="/public")
app.include_router(calendar_router, prefix="/calendar")
app.include_router(agent_router, prefix="/agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)