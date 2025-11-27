from datetime import datetime

from pydantic import BaseModel


class AgentPublicRequest(BaseModel):
    text: str
    requested_at: datetime | None = None


class AgentPublicResponse(BaseModel):
    input_text: str
    result: str


