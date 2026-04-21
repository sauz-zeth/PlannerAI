"""SQLAlchemy модели для аутентификации"""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, Index
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    telegram_id = Column(String, primary_key=True, index=True)
    google_user_id = Column(String, nullable=True, index=True)
    google_email = Column(String, nullable=True, index=True)  # Email пользователя Google
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OAuthToken(Base):
    """Модель для хранения OAuth токенов Google"""
    __tablename__ = "oauth_tokens"
    
    telegram_user_id = Column(String, primary_key=True, index=True)
    access_token = Column(Text, nullable=False)  # Используем Text для длинных токенов
    refresh_token = Column(Text, nullable=True)  # Может быть null для некоторых случаев
    expires_at = Column(BigInteger, nullable=False)  # Unix timestamp
    google_user_id = Column(String, nullable=False, index=True)
    google_email = Column(String, nullable=True, index=True)  # Email пользователя Google
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Индексы для часто используемых полей
    __table_args__ = (
        Index('idx_oauth_tokens_expires_at', 'expires_at'),
    )


class OAuthState(Base):
    """Модель для временного хранения OAuth state"""
    __tablename__ = "oauth_states"
    
    state = Column(String, primary_key=True, index=True)
    telegram_user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Индекс для автоматической очистки старых записей
    __table_args__ = (
        Index('idx_oauth_states_created_at', 'created_at'),
    )


class TelegramStatus(Base):
    """Модель для хранения статуса авторизации Telegram бота"""
    __tablename__ = "telegram_status"
    
    telegram_id = Column(String, primary_key=True, index=True)
    jwt_token = Column(Text, nullable=False)  # JWT токен для Telegram бота
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_used = Column(Boolean, default=False, nullable=False)  # Был ли токен использован
    
    # Индекс для очистки старых неиспользованных токенов
    __table_args__ = (
        Index('idx_telegram_status_created_at_used', 'created_at', 'is_used'),
    )


class RefreshToken(Base):
    """Модель для хранения refresh токенов JWT (опционально)"""
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(String, nullable=False, index=True)
    token = Column(Text, nullable=False)  # JWT refresh token
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Индексы для быстрого поиска и очистки
    __table_args__ = (
        Index('idx_refresh_tokens_user_id', 'telegram_user_id'),
        Index('idx_refresh_tokens_expires_at', 'expires_at'),
        Index('idx_refresh_tokens_revoked', 'is_revoked'),
    )