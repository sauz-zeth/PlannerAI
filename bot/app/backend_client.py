import httpx
from .config import settings

async def send_to_agent(text: str, requested_at):
    payload = {
        "text": text,
        "requested_at": requested_at.isoformat() if requested_at else None
    }

    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.post(
            f"{settings.BACKEND_URL}/agent",
            json=payload
        )
        resp.raise_for_status()
        return resp.json().get("result")