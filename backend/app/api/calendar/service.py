"""Сервис для работы с Google Calendar API"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.google_auth import GoogleCalendarService as GoogleAuthService
from ..config import CALENDAR_ID, TIMEZONE


class GoogleCalendarService:
    """Сервис для работы с Google Calendar API"""
    
    def __init__(self, telegram_user_id: str, session: AsyncSession):
        self.telegram_user_id = telegram_user_id
        self.session = session
        self._auth_service = None
    
    async def _get_service(self):
        """Получить или инициализировать сервис"""
        if not self._auth_service:
            self._auth_service = GoogleAuthService(self.telegram_user_id, self.session)
        return await self._auth_service.get_calendar_service()
    
    # Основные операции
    
    async def get_events(
        self, 
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None
    ) -> List[Dict]:
        """
        Получить события из календаря пользователя
        
        Args:
            max_results: Максимальное количество событий
            time_min: Начальная дата/время (ISO формат)
            time_max: Конечная дата/время (ISO формат)
            
        Returns:
            List[Dict]: Список событий
        """
        try:
            service = self._get_service()
            
            if not time_min:
                time_min = datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list( # type: ignore
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': event.get('id'),
                    'summary': event.get('summary', 'Без названия'),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'status': event.get('status'),
                    'htmlLink': event.get('htmlLink'),
                    'creator': event.get('creator', {}).get('email', ''),
                    'attendees': [
                        {'email': a.get('email'), 'responseStatus': a.get('responseStatus')}
                        for a in event.get('attendees', [])
                    ] if event.get('attendees') else []
                }
                formatted_events.append(formatted_event)
            
            return formatted_events
            
        except HttpError as error:
            raise Exception(f"Ошибка при получении событий: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,  # ✅ Исправлено здесь
        timezone: str = TIMEZONE
    ) -> Dict:
        """
        Создать новое событие в календаре пользователя
        
        Args:
            summary: Заголовок события
            start_time: Время начала (ISO формат)
            end_time: Время окончания (ISO формат)
            description: Описание события
            location: Место проведения
            attendees: Список email участников (опционально)
            timezone: Часовой пояс
            
        Returns:
            Dict: Созданное событие
        """
        try:
            service = await self._get_service()
            
            # Определяем формат времени (дата или дата+время)
            def format_time(time_str: str):
                if 'T' in time_str:
                    return {'dateTime': time_str, 'timeZone': timezone}
                else:
                    return {'date': time_str}
            
            # Подготавливаем участников
            attendee_list = []
            if attendees:
                for email in attendees:
                    attendee_list.append({'email': email})
            
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': format_time(start_time),
                'end': format_time(end_time),
            }
            
            if attendee_list:
                event['attendees'] = attendee_list
            
            created_event = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event
            ).execute()
            
            return {
                'id': created_event['id'],
                'summary': created_event['summary'],
                'description': created_event.get('description', ''),
                'start': created_event['start'].get('dateTime', created_event['start'].get('date')),
                'end': created_event['end'].get('dateTime', created_event['end'].get('date')),
                'htmlLink': created_event.get('htmlLink'),
                'status': created_event.get('status')
            }
            
        except HttpError as error:
            raise Exception(f"Ошибка при создании события: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    async def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict:
        """
        Обновить существующее событие пользователя
        
        Args:
            event_id: ID события
            summary: Новый заголовок (опционально)
            description: Новое описание (опционально)
            start_time: Новое время начала (опционально)
            end_time: Новое время окончания (опционально)
            location: Новое место (опционально)
            
        Returns:
            Dict: Обновленное событие
        """
        try:
            service = await self._get_service()
            
            # Сначала получаем текущее событие
            event = service.events().get(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            # Обновляем поля, если они переданы
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if location is not None:
                event['location'] = location
            
            # Обновляем время, если указано
            if start_time is not None:
                timezone = event['start'].get('timeZone', TIMEZONE)
                if 'T' in start_time:
                    event['start'] = {'dateTime': start_time, 'timeZone': timezone}
                else:
                    event['start'] = {'date': start_time}
            
            if end_time is not None:
                timezone = event['end'].get('timeZone', TIMEZONE)
                if 'T' in end_time:
                    event['end'] = {'dateTime': end_time, 'timeZone': timezone}
                else:
                    event['end'] = {'date': end_time}
            
            # Сохраняем изменения
            updated_event = service.events().update(
                calendarId=CALENDAR_ID,
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                'id': updated_event['id'],
                'summary': updated_event['summary'],
                'description': updated_event.get('description', ''),
                'start': updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                'end': updated_event['end'].get('dateTime', updated_event['end'].get('date')),
                'status': updated_event.get('status')
            }
            
        except HttpError as error:
            raise Exception(f"Ошибка при обновлении события: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    async def delete_event(self, event_id: str) -> bool:
        """
        Удалить событие из календаря пользователя
        
        Args:
            event_id: ID события
            
        Returns:
            bool: Успешно ли удалено
        """
        try:
            service = await self._get_service()
            
            service.events().delete(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            return True
            
        except HttpError as error:
            raise Exception(f"Ошибка при удалении события: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    async def get_event(self, event_id: str) -> Dict:
        """
        Получить конкретное событие пользователя по ID
        
        Args:
            event_id: ID события
            
        Returns:
            Dict: Информация о событии
        """
        try:
            service = await self._get_service()
            
            event = service.events().get(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            return {
                'id': event.get('id'),
                'summary': event.get('summary', ''),
                'description': event.get('description', ''),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'location': event.get('location', ''),
                'status': event.get('status'),
                'htmlLink': event.get('htmlLink')
            }
            
        except HttpError as error:
            raise Exception(f"Ошибка при получении события: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    # Дополнительные функции
    
    async def find_free_slots(
        self,
        date: str,
        duration_minutes: int = 60,
        start_hour: int = 9,
        end_hour: int = 18
    ) -> List[Dict]:
        """
        Найти свободные слоты на указанную дату для пользователя
        
        Args:
            date: Дата в формате YYYY-MM-DD
            duration_minutes: Продолжительность слота в минутах
            start_hour: Начальный час для поиска
            end_hour: Конечный час для поиска
            
        Returns:
            List[Dict]: Список свободных слотов
        """
        try:
            service = await self._get_service()
            
            # Преобразуем дату в диапазон времени
            time_min = f"{date}T00:00:00Z"
            time_max = f"{date}T23:59:59Z"
            
            # Получаем все события на день
            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Создаем список занятых слотов
            busy_slots = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Конвертируем в datetime объекты, если это время, а не дата
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    busy_slots.append((start_dt, end_dt))
            
            # Находим свободные слоты
            free_slots = []
            current_time = datetime.fromisoformat(f"{date}T{start_hour:02d}:00:00")
            end_time = datetime.fromisoformat(f"{date}T{end_hour:02d}:00:00")
            
            while current_time + timedelta(minutes=duration_minutes) <= end_time:
                slot_end = current_time + timedelta(minutes=duration_minutes)
                slot_free = True
                
                # Проверяем, не пересекается ли слот с занятыми событиями
                for busy_start, busy_end in busy_slots:
                    if not (slot_end <= busy_start or current_time >= busy_end):
                        slot_free = False
                        current_time = busy_end  # Перескакиваем на конец занятого слота
                        break
                
                if slot_free:
                    free_slots.append({
                        'start': current_time.strftime('%Y-%m-%dT%H:%M:%S'),
                        'end': slot_end.strftime('%Y-%m-%dT%H:%M:%S')
                    })
                    current_time = slot_end
                else:
                    current_time = max(current_time, slot_end)
            
            return free_slots
            
        except HttpError as error:
            raise Exception(f"Ошибка при поиске свободных слотов: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    async def search_events(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Поиск событий пользователя по тексту
        
        Args:
            query: Текст для поиска
            max_results: Максимальное количество результатов
            
        Returns:
            List[Dict]: Найденные события
        """
        try:
            service = await self._get_service()
            
            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [
                {
                    'id': e.get('id'),
                    'summary': e.get('summary', ''),
                    'start': e['start'].get('dateTime', e['start'].get('date')),
                    'end': e['end'].get('dateTime', e['end'].get('date')),
                    'description': e.get('description', '')
                }
                for e in events
            ]
            
        except HttpError as error:
            raise Exception(f"Ошибка при поиске событий: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    async def get_upcoming_events(self, hours: int = 24, max_results: int = 10) -> List[Dict]:
        """
        Получить ближайшие события пользователя
        
        Args:
            hours: Сколько часов вперед смотреть
            max_results: Максимальное количество событий
            
        Returns:
            List[Dict]: Ближайшие события
        """
        try:
            service = await self._get_service()
            
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(hours=hours)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return [
                {
                    'id': e.get('id'),
                    'summary': e.get('summary', 'Без названия'),
                    'start': e['start'].get('dateTime', e['start'].get('date')),
                    'end': e['end'].get('dateTime', e['end'].get('date')),
                    'time_to_event': self._get_time_to_event(e['start'].get('dateTime'))
                }
                for e in events
            ]
            
        except HttpError as error:
            raise Exception(f"Ошибка при получении ближайших событий: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    def _get_time_to_event(self, start_time: str) -> str:
        """Вычислить, сколько времени осталось до события"""
        if not start_time or 'T' not in start_time:
            return ""
        
        event_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        now = datetime.utcnow()
        
        if event_time < now:
            return "Уже прошло"
        
        diff = event_time - now
        
        if diff.days > 0:
            return f"Через {diff.days} дней"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"Через {hours} часов"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"Через {minutes} минут"
        else:
            return "Скоро"
    
    async def get_calendar_summary(self) -> Dict:
        """
        Получить краткую статистику по календарю пользователя
        """
        try:
            # Используем TIMEZONE из импортов
            
            # Или используйте UTC для консистентности
            from datetime import timezone
            
            now_utc = datetime.now(timezone.utc)
            
            # Сегодня в UTC
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1) - timedelta(seconds=1)
            
            # Завтра в UTC
            tomorrow_start = today_start + timedelta(days=1)
            tomorrow_end = tomorrow_start + timedelta(days=1) - timedelta(seconds=1)
            
            # Форматируем для API Google Calendar
            time_min_today = today_start.isoformat()
            time_max_today = today_end.isoformat()
            time_min_tomorrow = tomorrow_start.isoformat()
            time_max_tomorrow = tomorrow_end.isoformat()
            
            # Получаем события на сегодня
            today_events = await self.get_events(
                time_min=time_min_today,
                time_max=time_max_today
            )
            
            # Получаем события на завтра
            tomorrow_events = await self.get_events(
                time_min=time_min_tomorrow,
                time_max=time_max_tomorrow
            )
            
            # Получаем ближайшие события (следующие 24 часа)
            time_min_24h = now_utc.isoformat()
            time_max_24h = (now_utc + timedelta(hours=24)).isoformat()
            
            upcoming = await self.get_upcoming_events(hours=24)
            
            return {
                'today_events_count': len(today_events),
                'tomorrow_events_count': len(tomorrow_events),
                'next_24h_events_count': len(upcoming),
                'next_event': upcoming[0] if upcoming else None
            }
            
        except Exception as e:
            raise Exception(f"Ошибка при получении статистики: {e}")


# Фабрика для создания сервиса
def get_calendar_service(telegram_user_id: str, session: AsyncSession) -> GoogleCalendarService:
    """Создать сервис календаря для пользователя"""
    return GoogleCalendarService(telegram_user_id, session)