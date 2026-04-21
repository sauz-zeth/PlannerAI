from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .logic import handle_prompt
from ..database import get_db
from ..auth.dependencies import get_current_user

agent_router = APIRouter(tags=["Agent"])

class AgentPromptRequest(BaseModel):
    prompt: str

@agent_router.post("/prompt")
async def agent_prompt(
    body: AgentPromptRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await handle_prompt(
        prompt=body.prompt,
        user_id=current_user["telegram_id"],
        session=session,
    )