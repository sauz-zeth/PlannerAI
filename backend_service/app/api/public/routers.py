from datetime import datetime
from typing import Dict
from fastapi import APIRouter

public_router = APIRouter(tags=["public"])

from agent_service.logic import run_agent
from shared.schemas import AgentPublicRequest, AgentPublicResponse

@public_router.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@public_router.post("/agent", response_model=AgentPublicResponse)
async def agent_endpoint(payload: AgentPublicRequest) -> AgentPublicResponse:
    """
    Публичная точка входа для Telegram-бота.
    Backend вызывает агента как библиотеку без HTTP.
    """
    requested_at = payload.requested_at or datetime.utcnow()
    result = await run_agent(payload.text, requested_at)

    return AgentPublicResponse(
        input_text=payload.text,
        result=result
    )