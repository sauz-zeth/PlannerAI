"""Зависимости FastAPI для аутентификации"""
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .jwt_auth import verify_token
from .storage import get_tokens
from ..database import get_db

security = HTTPBearer(auto_error=False)


async def get_current_user(
    session: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    tg_id: Optional[str] = Query(None, include_in_schema=False)
) -> dict:
    """
    Получить текущего пользователя
    
    Поддерживает два способа:
    1. Bearer токен (рекомендуется)
    2. Query параметр tg_id (для обратной совместимости)
    """
    # Способ 1: Bearer токен
    if credentials:
        try:
            payload = verify_token(credentials.credentials)
            telegram_id = payload.get("sub")
            
            if not telegram_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Проверяем, что пользователь авторизован в Google
            google_tokens = await get_tokens(session, telegram_id)
            if not google_tokens:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated with Google"
                )
            
            return {
                "telegram_id": telegram_id,
                "google_user_id": payload.get("google_id"),
                "auth_method": "jwt"
            }
        except HTTPException:
            raise
        except Exception:
            # Если токен невалиден, пробуем query параметр
            pass
    
    # Способ 2: Query параметр (обратная совместимость, deprecated)
    if tg_id:
        google_tokens = await get_tokens(session, tg_id)
        if not google_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated with Google"
            )
        
        return {
            "telegram_id": tg_id,
            "google_user_id": google_tokens.google_user_id,
            "auth_method": "query_param"
        }
    
    # Ни один способ не сработал
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Use Authorization header or tg_id parameter",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def get_current_user_strict(
    session: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Получить текущего пользователя (только через JWT, строгий режим)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = verify_token(credentials.credentials)
    telegram_id = payload.get("sub")
    
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Проверяем, что пользователь авторизован в Google
    google_tokens = await get_tokens(session, telegram_id)
    if not google_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated with Google"
        )
    
    return {
        "telegram_id": telegram_id,
        "google_user_id": payload.get("google_id"),
        "auth_method": "jwt"
    }