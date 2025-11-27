from datetime import datetime
from typing import Dict

from fastapi import FastAPI

from agent_service.logic import run_agent
from shared import AgentPublicRequest, AgentPublicResponse

app = FastAPI(title="AI Planner Backend")


@app.post("/agent", response_model=AgentPublicResponse)
async def agent_endpoint(payload: AgentPublicRequest) -> AgentPublicResponse:
    """
    Публичная точка входа: вызывает агента как библиотеку внутри того же процесса.
    """
    requested_at = payload.requested_at or datetime.utcnow()
    result = await run_agent(payload.text, requested_at)
    return AgentPublicResponse(input_text=payload.text, result=result)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}