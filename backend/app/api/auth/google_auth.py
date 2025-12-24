"""Сервис для работы с Google Calendar API"""
import time
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import CLIENT_ID, CLIENT_SECRET
from .storage import get_tokens, save_tokens


class GoogleCalendarService:
    """Сервис для работы с Google Calendar API"""
    
    def __init__(self, telegram_user_id: str, session: AsyncSession):
        self.telegram_user_id = telegram_user_id
        self.session = session
        self.service = None
        self.creds = None
    
    async def get_calendar_service(self):
        """Получить сервис Google Calendar"""
        # Получаем токены из БД
        token_data = await get_tokens(self.session, self.telegram_user_id)
        if not token_data:
            raise Exception(f"Токены не найдены для пользователя {self.telegram_user_id}")
        
        # Проверяем, не истек ли access_token
        current_time = int(time.time())
        if token_data.expires_at <= current_time:
            # Токен истек, обновляем
            await self._refresh_access_token(token_data)
            token_data = await get_tokens(self.session, self.telegram_user_id)
        
        # Создаем credentials объект
        self.creds = Credentials(
            token=token_data.access_token, # type: ignore
            refresh_token=token_data.refresh_token, # type: ignore
            token_uri='https://oauth2.googleapis.com/token',
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/calendar.events']
        )
        
        # Создаем сервис Google Calendar
        self.service = build('calendar', 'v3', credentials=self.creds)
        return self.service
    
    async def _refresh_access_token(self, token_data):
        """Обновить access_token с помощью refresh_token"""
        try:
            creds = Credentials(
                token=token_data.access_token,
                refresh_token=token_data.refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/calendar.events']
            )
            
            creds.refresh(Request())
            
            # Сохраняем обновленные токены в БД
            await save_tokens(
                self.session,
                telegram_user_id=self.telegram_user_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token, # type: ignore
                expires_in=3600,
                google_user_id=token_data.google_user_id
            )
        except Exception as e:
            raise Exception(f"Не удалось обновить токен: {str(e)}")
    
    async def test_connection(self):
        """Протестировать подключение к Google Calendar"""
        try:
            service = await self.get_calendar_service()
            calendar_list = service.calendarList().list().execute()
            return True
        except HttpError as e:
            if e.resp.status == 401:
                raise Exception("Неавторизован. Токены невалидны.")
            raise Exception(f"Ошибка подключения: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка: {str(e)}")