import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.database import init_db, close_db, async_session_maker
from app.bot.handlers import router as bot_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
dp.include_router(bot_router)


async def on_startup() -> None:
    """Run on application startup"""
    logger.info("Starting application...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start bot polling in background
    asyncio.create_task(dp.start_polling(bot, session=async_session_maker()))
    logger.info("Bot polling started")


async def on_shutdown() -> None:
    """Run on application shutdown"""
    logger.info("Shutting down application...")
    
    # Close bot session
    await bot.session.close()
    logger.info("Bot session closed")
    
    # Close database
    await close_db()
    logger.info("Database closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    await on_startup()
    yield
    await on_shutdown()


# Create FastAPI app
app = FastAPI(
    title="Calendar AI Bot",
    description="AI-powered calendar management Telegram bot",
    version="0.1.0",
    lifespan=lifespan,
)


# Middleware to inject database session
@dp.update.middleware()
async def db_session_middleware(handler, event, data):
    """Inject database session into handlers"""
    async with async_session_maker() as session:
        data["session"] = session
        return await handler(event, data)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Calendar AI Bot",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "bot": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )