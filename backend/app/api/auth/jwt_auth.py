"""JWT аутентификация - упрощенная версия"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

# Секретный ключ из переменных окружения
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_EXPIRE_DAYS = 90

def create_access_token(
    telegram_user_id: str,
    google_user_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Создать JWT access token"""
    to_encode = {
        "sub": telegram_user_id,
        "type": "access",
        "iat": datetime.utcnow()
    }
    
    if google_user_id:
        to_encode["google_id"] = google_user_id
    
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode["exp"] = expire
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(telegram_user_id: str) -> str:
    """Создать refresh token"""
    to_encode = {
        "sub": telegram_user_id,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    """Проверить и декодировать JWT токен"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )