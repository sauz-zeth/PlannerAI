"""Клиент для работы с Backend API"""
import httpx
from typing import Optional, Dict, Any, List

try:
    from .config import BACKEND_API_URL
except ImportError:
    # Для запуска напрямую
    from config import BACKEND_API_URL


class APIClient:
    """Клиент для взаимодействия с Backend API"""
    
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or BACKEND_API_URL).rstrip('/')
        self.client = None
    
    async def _get_client(self):
        """Получить или создать HTTP клиент"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Выполнить HTTP запрос к API"""
        try:
            client = await self._get_client()
            url = f"{self.base_url}{endpoint}"
            
            headers = {
                "accept": "application/json",
                "User-Agent": "Telegram-Bot/1.0"
            }
            
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            # Для отладки
            print(f"DEBUG: Making {method} request to {url}")
            print(f"DEBUG: Params: {params}")
            
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                follow_redirects=True
            )
            
            # Логируем ответ для отладки
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response headers: {dict(response.headers)}")
            
            if response.status_code >= 400:
                error_text = response.text[:500] if response.text else "No error text"
                print(f"DEBUG: Error response: {error_text}")
                
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", str(error_data))
                    raise Exception(f"API Error {response.status_code}: {error_detail}")
                except:
                    raise Exception(f"API Error {response.status_code}: {error_text}")
            
            return response.json()
            
        except httpx.RequestError as e:
            error_msg = f"Connection error: {str(e)}"
            print(f"DEBUG: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            print(f"DEBUG: Unexpected error: {str(e)}")
            raise
    
    async def close(self):
        """Закрыть HTTP клиент"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    # Авторизация
    async def get_auth_status(self, telegram_user_id: str) -> Dict[str, Any]:
        """Проверить статус авторизации для Telegram пользователя"""
        return await self._request(
            "GET",
            "/auth/telegram-status",
            params={"telegram_user_id": telegram_user_id}
        )
    
    # Команды календаря
    async def get_events(
        self,
        token: str,
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Получить события пользователя"""
        params = {"max_results": max_results}
        if time_min:
            params["time_min"] = time_min
        if time_max:
            params["time_max"] = time_max
        
        return await self._request(
            "GET",
            "/calendar/calendar/events",
            token=token,
            params=params
        )
    
    async def get_event(self, token: str, event_id: str) -> Dict[str, Any]:
        """Получить конкретное событие"""
        return await self._request(
            "GET",
            f"/calendar/calendar/events/{event_id}",
            token=token
        )
    
    async def create_event(
        self,
        token: str,
        summary: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        timezone: str = "Europe/Moscow"
    ) -> Dict[str, Any]:
        """Создать новое событие"""
        json_data = {
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "timezone": timezone
        }
        
        if description:
            json_data["description"] = description
        if location:
            json_data["location"] = location
        if attendees:
            json_data["attendees"] = attendees
        
        return await self._request(
            "POST",
            "/calendar/calendar/events",
            token=token,
            json_data=json_data
        )
    
    async def update_event(
        self,
        token: str,
        event_id: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Обновить событие"""
        json_data = {}
        if summary:
            json_data["summary"] = summary
        if description:
            json_data["description"] = description
        if start_time:
            json_data["start_time"] = start_time
        if end_time:
            json_data["end_time"] = end_time
        if location:
            json_data["location"] = location
        
        return await self._request(
            "PUT",
            f"/calendar/calendar/events/{event_id}",
            token=token,
            json_data=json_data
        )
    
    async def delete_event(self, token: str, event_id: str) -> Dict[str, Any]:
        """Удалить событие"""
        return await self._request(
            "DELETE",
            f"/calendar/calendar/events/{event_id}",
            token=token
        )
    
    async def search_events(
        self,
        token: str,
        query: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Поиск событий по тексту"""
        return await self._request(
            "GET",
            "/calendar/calendar/search",
            token=token,
            params={"query": query, "max_results": max_results}
        )
    
    async def get_upcoming_events(
        self,
        token: str,
        hours: int = 24,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Получить ближайшие события"""
        return await self._request(
            "GET",
            "/calendar/calendar/upcoming",
            token=token,
            params={"hours": hours, "max_results": max_results}
        )
    
    async def get_calendar_summary(self, token: str) -> Dict[str, Any]:
        """Получить статистику календаря"""
        return await self._request(
            "GET",
            "/calendar/calendar/summary",
            token=token
        )
    
    async def get_calendar_status(self, token: str) -> Dict[str, Any]:
        """Проверить статус подключения к календарю"""
        return await self._request(
            "GET",
            "/calendar/calendar/status",
            token=token
        )
    
    async def get_free_blocks(self, token: str, date: str) -> List[Dict[str, Any]]:
        """Свободные промежутки между событиями за весь день"""
        return await self._request(
            "GET",
            "/calendar/calendar/free-blocks",
            token=token,
            params={"date": date},
        )

    async def find_free_slots(
        self,
        token: str,
        date: str,
        duration_minutes: int = 60,
        start_hour: int = 9,
        end_hour: int = 18
    ) -> List[Dict[str, Any]]:
        """Найти свободные слоты"""
        json_data = {
            "date": date,
            "duration_minutes": duration_minutes,
            "start_hour": start_hour,
            "end_hour": end_hour
        }
        
        return await self._request(
            "POST",
            "/calendar/calendar/free-slots",
            token=token,
            json_data=json_data
        )
    
    # Дополнительные методы для тестирования
    async def test_connection(self) -> Dict[str, Any]:
        """Проверить подключение к API"""
        try:
            return await self._request("GET", "/")
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def get_telegram_auth_url(self, telegram_user_id: str) -> Dict[str, Any]:
        """Получить URL для авторизации через Telegram"""
        return await self._request(
            "GET",
            "/auth/login",
            params={"tg_id": telegram_user_id}
        )

    async def send_agent_prompt(
        self,
        token: str,
        prompt: str
    ) -> Dict[str, Any]:
        """Отправить промт агенту"""
        return await self._request(
            method="POST",
            endpoint="/agent/prompt",
            token=token,
            json_data={"prompt": prompt},
        )