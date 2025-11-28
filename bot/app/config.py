from pydantic import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    BACKEND_URL: str = "http://127.0.0.1:8000"

settings = Settings()