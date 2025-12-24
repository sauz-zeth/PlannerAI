"""Хранилище OAuth токенов и состояний в БД"""
import time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timedelta

from .models import OAuthToken, OAuthState, User
from ..schemas import TokenData


async def save_state(session: AsyncSession, state: str, telegram_user_id: str):
    """Сохранить OAuth state"""
    oauth_state = OAuthState(state=state, telegram_user_id=telegram_user_id)
    session.add(oauth_state)
    await session.commit()


async def pop_state(session: AsyncSession, state: str) -> Optional[str]:
    """Получить и удалить OAuth state"""
    result = await session.execute(
        select(OAuthState).where(OAuthState.state == state)
    )
    oauth_state = result.scalar_one_or_none()
    if oauth_state:
        telegram_user_id = oauth_state.telegram_user_id
        await session.delete(oauth_state)
        await session.commit()
        return telegram_user_id
    return None


async def save_tokens(
    session: AsyncSession,
    telegram_user_id: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    google_user_id: str
):
    """Сохранить OAuth токены"""
    expires_at = int(time.time()) + expires_in
    
    # Проверяем, существует ли запись
    result = await session.execute(
        select(OAuthToken).where(OAuthToken.telegram_user_id == telegram_user_id)
    )
    token = result.scalar_one_or_none()
    
    if token:
        # Обновляем существующую запись
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at
        token.google_user_id = google_user_id
    else:
        # Создаем новую запись
        token = OAuthToken(
            telegram_user_id=telegram_user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        google_user_id=google_user_id
    )
        session.add(token)
    
    # Создаем или обновляем пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(telegram_id=telegram_user_id, google_user_id=google_user_id)
        session.add(user)
    else:
        user.google_user_id = google_user_id
    
    await session.commit()


async def get_tokens(session: AsyncSession, telegram_user_id: str) -> Optional[TokenData]:
    """Получить OAuth токены"""
    result = await session.execute(
        select(OAuthToken).where(OAuthToken.telegram_user_id == telegram_user_id)
    )
    token = result.scalar_one_or_none()
    
    if not token:
        return None
    
    return TokenData(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        expires_at=token.expires_at,
        google_user_id=token.google_user_id
    )


async def cleanup_old_states(session: AsyncSession, hours: int = 24):
    """Очистить старые OAuth states (старше указанного количества часов)"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    await session.execute(
        delete(OAuthState).where(OAuthState.created_at < cutoff_time)
    )
    await session.commit()
