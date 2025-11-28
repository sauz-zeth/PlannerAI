from datetime import datetime

from pydantic import BaseModel

class AgentPublicRequest(BaseModel):
    text: str
    requested_at: datetime | None = None

class AgentPublicResponse(BaseModel):
    input_text: str
    result: str

class EventCreate(BaseModel):
    token: str
    title: str
    start: str   # ISO datetime string: "2025-11-30T18:00:00+03:00"
    end: str

class IcsEvent(BaseModel):
    uid: str
    title: str
    start: str   # ISO datetime string
    end: str