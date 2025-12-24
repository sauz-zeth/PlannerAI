"""SQLAlchemy модели для аутентификации"""
from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.sql import func
from datetime import datetime
from ..database import Base


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    telegram_id = Column(String, primary_key=True, index=True)
    google_user_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OAuthToken(Base):
    """Модель для хранения OAuth токенов Google"""
    __tablename__ = "oauth_tokens"
    
    telegram_user_id = Column(String, primary_key=True, index=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(Integer, nullable=False)
    google_user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


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


