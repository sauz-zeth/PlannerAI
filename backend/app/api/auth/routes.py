"""Роуты для аутентификации"""
import secrets
import httpx
import base64
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from ..config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPE, TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME
from ..database import get_db
from .storage import save_state, pop_state, save_tokens, get_tokens, mark_telegram_ready, is_telegram_ready
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

        # Получаем Google user info
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        userinfo = userinfo_response.json()
        google_user_id = userinfo.get("id")
        google_email = userinfo.get("email", "")

    if not google_user_id:
        raise HTTPException(status_code=400, detail="Failed to get Google user ID")

    # Сохраняем Google токены в БД
    await save_tokens(session, tg_id, access_token, refresh_token, expires_in, google_user_id, google_email)

    # Создаем JWT токен для нашего API
    jwt_token = create_access_token(tg_id, google_user_id)
    
    # Отмечаем, что пользователь авторизован в Google и готов к подключению Telegram бота
    await mark_telegram_ready(session, tg_id, jwt_token)

    # Показываем страницу успеха
    success_message = f"""
        <div style="margin: 30px 0; padding: 25px; background: #e8f5e9; border-radius: 10px; text-align: center;">
            <h3 style="color: #2e7d32; margin: 0 0 15px 0;">✅ Google Calendar успешно подключён!</h3>
            <p style="color: #2e7d32; margin: 0 0 20px 0; font-size: 16px;">
                Вы подключили аккаунт: <strong>{google_email}</strong>
            </p>
            <div style="margin: 20px 0; padding: 15px; background: #f1f8e9; border-radius: 8px; text-align: left;">
                <h4 style="color: #33691e; margin: 0 0 10px 0;">🎯 Что делать дальше:</h4>
                <ol style="margin: 0; padding-left: 20px; color: #333;">
                    <li style="margin-bottom: 8px;">Вернитесь в Telegram</li>
                    <li style="margin-bottom: 8px;">Напишите в чат с ботом команду: <code>/check</code></li>
                    <li>Бот автоматически подключится к вашему календарю</li>
                </ol>
            </div>
            <div style="margin-top: 25px; padding: 15px; background: #fffde7; border-radius: 8px;">
                <p style="margin: 0; color: #f57f17; font-size: 14px;">
                    ⚠️ <strong>Важно:</strong> Закройте эту вкладку после возвращения в Telegram
                </p>
            </div>
        </div>
    """

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>✅ Авторизация успешна</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                margin: 0;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                max-width: 500px;
                width: 100%;
            }}
            .success-icon {{
                font-size: 60px;
                color: #4CAF50;
                margin-bottom: 20px;
            }}
            .telegram-button {{
                display: inline-block;
                background: #0088cc;
                color: white;
                text-decoration: none;
                padding: 15px 30px;
                border-radius: 10px;
                font-weight: bold;
                margin-top: 20px;
                transition: background 0.3s;
            }}
            .telegram-button:hover {{
                background: #006699;
            }}
            .command-box {{
                background: #f5f5f5;
                padding: 12px 20px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
                display: inline-block;
                border: 2px dashed #ddd;
            }}
            @media (max-width: 600px) {{
                .container {{
                    padding: 25px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="text-align: center;">
                <div class="success-icon">✅</div>
                <h1 style="color: #333; margin: 0 0 10px 0;">Авторизация завершена!</h1>
                <p style="color: #666; margin: 0 0 30px 0; line-height: 1.6;">
                    Аккаунт <strong>{google_email}</strong> успешно подключён к Google Calendar
                </p>
                
                {success_message}
                
                <div style="margin-top: 30px;">
                    <div style="color: #666; font-size: 14px; margin-bottom: 15px;">
                        Перейдите в Telegram и используйте команду:
                    </div>
                    <div class="command-box">/check</div>
                </div>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #999;">
                    <p style="margin: 5px 0;">Эта страница может быть закрыта</p>
                    <p style="margin: 5px 0;">Процесс авторизации завершён</p>
                </div>
            </div>
        </div>
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
            "google_email": tokens_data.google_email,
            "has_access_token": bool(tokens_data.access_token),
            "has_refresh_token": bool(tokens_data.refresh_token),
            "expires_at": datetime.fromtimestamp(tokens_data.expires_at).isoformat()
        }
    }


@auth_router.get("/telegram-status")
async def telegram_auth_status(
    telegram_user_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Проверить статус авторизации для Telegram бота
    Упрощенная версия без проверки времени токена
    """
    try:
        # Проверяем, авторизован ли пользователь в Google
        google_tokens = await get_tokens(session, telegram_user_id)
        
        if not google_tokens:
            return {
                "authenticated": False,
                "message": "Вы еще не авторизовались через Google. Используйте /login",
                "ready": False
            }
        
        # Проверяем, готов ли пользователь к подключению Telegram бота
        ready_data = await is_telegram_ready(session, telegram_user_id)
        
        if not ready_data or not ready_data.get("jwt_token"):
            return {
                "authenticated": False,
                "message": "Завершите авторизацию в Google. Используйте /login",
                "ready": False
            }
        
        # Просто возвращаем токен без проверки времени
        # (можно добавить проверку позже)
        jwt_token = ready_data["jwt_token"]
        
        return {
            "authenticated": True,
            "ready": True,
            "jwt_token": jwt_token,
            "user_info": {
                "telegram_id": telegram_user_id,
                "google_email": google_tokens.google_email,
                "google_user_id": google_tokens.google_user_id
            },
            "message": "✅ Авторизация успешна! Бот подключен к вашему Google Calendar."
        }
    
    except Exception as e:
        print(f"ERROR in telegram_auth_status: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "authenticated": False,
            "ready": False,
            "message": f"Ошибка сервера: {str(e)[:100]}"
        }
