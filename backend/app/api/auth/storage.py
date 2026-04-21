"""Хранилище OAuth токенов, состояний и статусов Telegram в БД"""
import time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from datetime import datetime, timedelta

from .models import OAuthToken, OAuthState, User, TelegramStatus
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
    google_user_id: str,
    google_email: str = ""
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
        token.google_email = google_email
    else:
        # Создаем новую запись
        token = OAuthToken(
            telegram_user_id=telegram_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            google_user_id=google_user_id,
            google_email=google_email
        )
        session.add(token)
    
    # Создаем или обновляем пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            telegram_id=telegram_user_id, 
            google_user_id=google_user_id,
            google_email=google_email
        )
        session.add(user)
    else:
        user.google_user_id = google_user_id
        user.google_email = google_email
    
    await session.commit()


async def get_tokens(session: AsyncSession, telegram_user_id: str) -> Optional[OAuthToken]:
    """Получить OAuth токены"""
    result = await session.execute(
        select(OAuthToken).where(OAuthToken.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def get_tokens_data(session: AsyncSession, telegram_user_id: str) -> Optional[TokenData]:
    """Получить OAuth токены в виде TokenData"""
    token = await get_tokens(session, telegram_user_id)
    
    if not token:
        return None
    
    return TokenData(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        expires_at=token.expires_at,
        google_user_id=token.google_user_id,
        google_email=token.google_email
    )


async def mark_telegram_ready(
    session: AsyncSession, 
    telegram_id: str, 
    jwt_token: str
):
    """Отметить, что пользователь готов к подключению Telegram бота"""
    # Удаляем старый статус если есть
    await session.execute(
        delete(TelegramStatus).where(TelegramStatus.telegram_id == telegram_id)
    )
    
    # Создаем новый статус
    status = TelegramStatus(
        telegram_id=telegram_id,
        jwt_token=jwt_token,
        created_at=datetime.utcnow(),
        is_used=False
    )
    session.add(status)
    await session.commit()


async def is_telegram_ready(session: AsyncSession, telegram_id: str):
    """Проверить, готов ли пользователь к подключению Telegram бота"""
    result = await session.execute(
        select(TelegramStatus)
        .where(TelegramStatus.telegram_id == telegram_id)
        .where(TelegramStatus.is_used == False)
    )
    status = result.scalar_one_or_none()
    
    if status:
        return {
            "jwt_token": status.jwt_token,
            "created_at": status.created_at,
            "is_used": status.is_used
        }
    return None


async def mark_telegram_used(session: AsyncSession, telegram_id: str):
    """Отметить, что JWT токен был использован Telegram ботом"""
    result = await session.execute(
        select(TelegramStatus)
        .where(TelegramStatus.telegram_id == telegram_id)
        .where(TelegramStatus.is_used == False)
    )
    status = result.scalar_one_or_none()
    
    if status:
        status.is_used = True
        await session.commit()
        return True
    return False


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: str) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def update_token_expiry(
    session: AsyncSession,
    telegram_user_id: str,
    new_access_token: str,
    new_expires_in: int
):
    """Обновить access token и его срок действия"""
    result = await session.execute(
        select(OAuthToken).where(OAuthToken.telegram_user_id == telegram_user_id)
    )
    token = result.scalar_one_or_none()
    
    if token:
        token.access_token = new_access_token
        token.expires_at = int(time.time()) + new_expires_in
        await session.commit()
        return True
    return False


async def delete_tokens(session: AsyncSession, telegram_user_id: str):
    """Удалить токены пользователя (при logout)"""
    # Удаляем OAuth токены
    await session.execute(
        delete(OAuthToken).where(OAuthToken.telegram_user_id == telegram_user_id)
    )
    
    # Удаляем Telegram статус
    await session.execute(
        delete(TelegramStatus).where(TelegramStatus.telegram_id == telegram_user_id)
    )
    
    # Очищаем Google ID у пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.google_user_id = None
        user.google_email = None
    
    await session.commit()


async def cleanup_old_states(session: AsyncSession, hours: int = 24):
    """Очистить старые OAuth states (старше указанного количества часов)"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    await session.execute(
        delete(OAuthState).where(OAuthState.created_at < cutoff_time)
    )
    await session.commit()


async def cleanup_old_telegram_status(session: AsyncSession, minutes: int = 30):
    """Очистить старые Telegram статусы (старше указанного количества минут)"""
    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
    await session.execute(
        delete(TelegramStatus)
        .where(
            (TelegramStatus.created_at < cutoff_time) &
            (TelegramStatus.is_used == False)
        )
    )
    await session.commit()