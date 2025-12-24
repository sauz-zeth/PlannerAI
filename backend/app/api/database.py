"""Настройка подключения к базе данных"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

# PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://ai_planner:ai_planner_pass@localhost:5432/ai_planner"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession: # type: ignore
    """Dependency для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session # type: ignore
        finally:
            await session.close()


async def init_db():
    """Инициализация БД - создание таблиц"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


