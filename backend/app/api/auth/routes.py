"""Роуты для аутентификации"""
import secrets
import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPE
from ..database import get_db
from .storage import save_state, pop_state, save_tokens, get_tokens
from .jwt_auth import create_access_token, create_refresh_token, verify_token
from .dependencies import get_current_user

auth_router = APIRouter(tags=["auth"])


@auth_router.get("/login")
async def google_login(tg_id: str, session: AsyncSession = Depends(get_db)):
    """Начать OAuth авторизацию Google"""
    state = secrets.token_urlsafe(16)
    await save_state(session, state, tg_id)

    oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        f"&scope={SCOPE}"
        "&access_type=offline"
        "&prompt=consent"
        f"&state={state}"
    )
    return RedirectResponse(url=oauth_url)


@auth_router.get("/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    session: AsyncSession = Depends(get_db)
):
    """Обработка callback от Google OAuth"""
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    tg_id = await pop_state(session, state)
    if not tg_id:
        raise HTTPException(status_code=403, detail="Invalid state")

    # Обмен code → Google tokens и получение userinfo в рамках одного клиента
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch tokens")

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # Получаем Google user id
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        userinfo = userinfo_response.json()
        google_user_id = userinfo.get("id")

    if not google_user_id:
        raise HTTPException(status_code=400, detail="Failed to get Google user ID")

    # Сохраняем Google токены в БД
    await save_tokens(session, tg_id, access_token, refresh_token, expires_in, google_user_id)

    # Создаем JWT токены для нашего API
    jwt_token = create_access_token(tg_id, google_user_id)
    refresh_token_jwt = create_refresh_token(tg_id)

    return HTMLResponse(f"""
    <html>
        <head><title>✅ Авторизация успешна</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>✅ Google Calendar подключён!</h2>
            <p>Ваш JWT токен:</p>
            <textarea style="width: 100%; height: 60px; font-family: monospace;" readonly>
{jwt_token}
            </textarea>
            <p>Используйте его в заголовке:</p>
            <code style="background: #f4f4f4; padding: 5px; display: block;">
Authorization: Bearer {jwt_token}
            </code>
            <p>Refresh token (сохраните для обновления):</p>
            <textarea style="width: 100%; height: 60px; font-family: monospace;" readonly>
{refresh_token_jwt}
            </textarea>
            <p><a href="/docs" target="_blank">Перейти к документации API</a></p>
        </body>
    </html>
    """)


@auth_router.post("/refresh")
async def refresh_token_endpoint(
    refresh_token: str,
    session: AsyncSession = Depends(get_db)
):
    """Обновить access token с помощью refresh token"""
    try:
        payload = verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Not a refresh token")
        
        telegram_id = payload.get("sub")
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Invalid refresh token")
        
        # Проверяем, что пользователь все еще авторизован в Google
        google_tokens = await get_tokens(session, telegram_id)
        if not google_tokens:
            raise HTTPException(status_code=400, detail="User not authenticated with Google")
        
        # Создаем новый access token
        new_access_token = create_access_token(telegram_id, google_tokens.google_user_id)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 30 * 24 * 3600
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {str(e)}")


@auth_router.get("/validate")
async def validate_token_endpoint(current_user: dict = Depends(get_current_user)):
    """Проверить валидность токена"""
    return {
        "valid": True,
        "user": current_user,
        "message": "Token is valid"
    }


@auth_router.get("/tokens")
async def get_tokens_endpoint(
    telegram_user_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Получить информацию о токенах пользователя (для отладки)"""
    tokens_data = await get_tokens(session, telegram_user_id)
    
    if not tokens_data:
        return {"tokens": None, "message": "User not found"}
    
    return {
        "tokens": {
        "telegram_id": telegram_user_id,
        "google_user_id": tokens_data.google_user_id,
        "has_access_token": bool(tokens_data.access_token),
        "has_refresh_token": bool(tokens_data.refresh_token),
        "expires_at": datetime.fromtimestamp(tokens_data.expires_at).isoformat()
    }
    }