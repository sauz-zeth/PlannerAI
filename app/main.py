import asyncio
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from .agent import run_agent
from .bot import run_bot_polling


class AgentRequest(BaseModel):
    text: str


class AgentResponse(BaseModel):
    input_text: str
    result: str


app = FastAPI(title="AI Planner Vibe - Voice Bot & Agent")


@app.on_event("startup")
async def startup_event() -> None:
    """
    При старте FastAPI-приложения запускаем Telegram-бота в отдельной задаче.
    """
    asyncio.create_task(run_bot_polling())


@app.post("/agent", response_model=AgentResponse)
async def agent_endpoint(payload: AgentRequest) -> Dict[str, Any]:
    """
    Минимальный HTTP-эндпоинт агента:
    принимает текст и возвращает результат работы агента.
    """
    result = await run_agent(payload.text)
    return {"input_text": payload.text, "result": result}


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


