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
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========
    
    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Преобразовать строку времени в datetime с временной зоной"""
        if not datetime_str:
            return None
        
        try:
            # Если строка заканчивается на Z, заменяем на +00:00
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str.replace('Z', '+00:00')
            
            # Парсим datetime
            dt = datetime.fromisoformat(datetime_str)
            
            # Если datetime не имеет временной зоны, добавляем UTC
            if dt.tzinfo is None:
                from datetime import timezone
                dt = dt.replace(tzinfo=timezone.utc)
                
            return dt
        except ValueError:
            # Если это только дата (без времени), возвращаем None
            if 'T' not in datetime_str:
                return None
            raise
    
    def _format_readable_datetime(self, datetime_str: str) -> str:
        """Форматировать дату/время в читаемый формат"""
        if not datetime_str:
            return ""
        
        try:
            dt = self._parse_datetime(datetime_str)
            if not dt:
                # Если это только дата (без времени)
                try:
                    # Пробуем распарсить дату
                    date_only = datetime.strptime(datetime_str, "%Y-%m-%d")
                    months = {
                        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
                    }
                    return f"{date_only.day} {months[date_only.month]}"
                except ValueError:
                    return datetime_str
            
            # Для событий сегодня/завтра
            from datetime import timezone
            now = datetime.now(timezone.utc)
            
            # Преобразуем now в ту же временную зону
            if dt.tzinfo:
                now = now.astimezone(dt.tzinfo)
            
            if dt.date() == now.date():
                return f"Сегодня в {dt.strftime('%H:%M')}"
            elif dt.date() == (now.date() + timedelta(days=1)):
                return f"Завтра в {dt.strftime('%H:%M')}"
            else:
                # Русские названия месяцев
                months = {
                    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
                }
                return f"{dt.day} {months[dt.month]} в {dt.strftime('%H:%M')}"
                
        except Exception:
            # В случае ошибки возвращаем оригинальную строку
            return datetime_str
    
    def _get_event_duration(self, start_time: str, end_time: str) -> str:
        """Получить продолжительность события в читаемом формате"""
        if not start_time or not end_time:
            return ""
        
        # Проверяем, есть ли время в формате (содержит 'T')
        has_time = 'T' in start_time and 'T' in end_time
        
        try:
            start_dt = self._parse_datetime(start_time)
            end_dt = self._parse_datetime(end_time)
            
            if not start_dt or not end_dt:
                return ""
            
            duration = end_dt - start_dt
            
            # Если это целый день (без времени)
            if not has_time:
                days = duration.days
                if days == 1:
                    return "1 день"
                else:
                    return f"{days} дней"
            
            # Преобразуем в часы и минуты
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            if hours > 0 and minutes > 0:
                return f"{hours} ч {minutes} мин"
            elif hours > 0:
                return f"{hours} ч"
            elif minutes > 0:
                return f"{minutes} мин"
            else:
                return "менее минуты"
                
        except Exception:
            return ""
    
    def _get_time_to_event(self, start_time: str) -> str:
        """Вычислить, сколько времени осталось до события"""
        if not start_time or 'T' not in start_time:
            return ""
        
        # Преобразуем строку в datetime с временной зоной
        event_time = self._parse_datetime(start_time)
        if not event_time:
            return ""
        
        # Получаем текущее время с временной зоной (UTC)
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        # Приводим к одинаковой временной зоне
        if event_time.tzinfo:
            now = now.astimezone(event_time.tzinfo)
        else:
            event_time = event_time.replace(tzinfo=timezone.utc)
        
        if event_time < now:
            return "Уже прошло"
        
        diff = event_time - now
        
        if diff.days > 0:
            if diff.days == 1:
                return "Завтра"
            elif diff.days < 7:
                return f"Через {diff.days} дня"
            else:
                return f"Через {diff.days} дней"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            if hours == 1:
                return "Через 1 час"
            elif hours < 5:
                return f"Через {hours} часа"
            else:
                return f"Через {hours} часов"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            if minutes == 1:
                return "Через 1 минуту"
            elif minutes < 5:
                return f"Через {minutes} минуты"
            else:
                return f"Через {minutes} минут"
        else:
            return "Скоро"
    
    def _format_events_for_detailed_response(self, events: List[Dict]) -> str:
        """Форматировать события для подробного ответа"""
        if not events:
            return "Событий не найдено."
        
        result = []
        for i, event in enumerate(events, 1):
            event_text = f"{i}. {event.get('summary', 'Без названия')}"
            
            # Время
            if event.get('readable_start'):
                event_text += f"\n   📅 Время: {event.get('readable_start')}"
                if event.get('readable_end') and event.get('readable_start') != event.get('readable_end'):
                    event_text += f" - {event.get('readable_end')}"
            
            # Продолжительность
            if event.get('duration'):
                event_text += f"\n   ⏱️ Продолжительность: {event.get('duration')}"
            
            # До события
            if event.get('time_to_event'):
                event_text += f"\n   🕐 {event.get('time_to_event')}"
            
            # Описание
            if event.get('description'):
                desc = event['description']
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                event_text += f"\n   📝 Описание: {desc}"
            
            # Место
            if event.get('location'):
                event_text += f"\n   📍 Место: {event.get('location')}"
            
            # Участники
            if event.get('attendee_count', 0) > 0:
                event_text += f"\n   👥 Участников: {event.get('attendee_count')}"
            
            result.append(event_text)
        
        return "\n\n".join(result)
    
    # ========== ОСНОВНЫЕ ОПЕРАЦИИ ==========
    
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
            service = await self._get_service()
            
            if not time_min:
                from datetime import timezone
                time_min = datetime.now(timezone.utc).isoformat()
            
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
                start_time = event['start'].get('dateTime', event['start'].get('date'))
                end_time = event['end'].get('dateTime', event['end'].get('date'))
                
                formatted_event = {
                    'id': event.get('id'),
                    'summary': event.get('summary', 'Без названия'),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start': start_time,
                    'end': end_time,
                    'readable_start': self._format_readable_datetime(start_time),
                    'readable_end': self._format_readable_datetime(end_time),
                    'duration': self._get_event_duration(start_time, end_time),
                    'time_to_event': self._get_time_to_event(start_time),
                    'status': event.get('status'),
                    'htmlLink': event.get('htmlLink'),
                    'creator': event.get('creator', {}).get('email', ''),
                    'attendee_count': len(event.get('attendees', [])) if event.get('attendees') else 0
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
        attendees: Optional[List[str]] = None,
        timezone: str = "Europe/Moscow"  # Явно указываем Moscow
    ) -> Dict:
        """
        Создать новое событие в календаре пользователя
        
        Args:
            summary: Заголовок события
            start_time: Время начала (ISO формат с Z для UTC или без)
            end_time: Время окончания (ISO формат с Z для UTC или без)
            description: Описание события
            location: Место проведения
            attendees: Список email участников (опционально)
            timezone: Часовой пояс (по умолчанию Москва)
        """
        try:
            print(f"🎬 СОЗДАНИЕ СОБЫТИЯ В КАЛЕНДАРЕ:")
            print(f"   Название: {summary}")
            print(f"   Начало (получено): {start_time}")
            print(f"   Конец (получено): {end_time}")
            print(f"   Часовой пояс: {timezone}")
            
            service = await self._get_service()
            
            # Функция для форматирования времени с явным часовым поясом
            def format_time(time_str: str):
                if 'T' in time_str:
                    # Если время в UTC (заканчивается на Z), конвертируем в строку без Z
                    # и указываем часовой пояс
                    if time_str.endswith('Z'):
                        # Убираем Z и указываем часовой пояс
                        return {
                            'dateTime': time_str[:-1],  # Убираем Z
                            'timeZone': timezone
                        }
                    else:
                        # Уже с часовым поясом или без
                        return {'dateTime': time_str, 'timeZone': timezone}
                else:
                    # Дата без времени
                    return {'date': time_str}
            
            # Логируем отформатированное время
            start_formatted = format_time(start_time)
            end_formatted = format_time(end_time)
            print(f"   Начало (для Google): {start_formatted}")
            print(f"   Конец (для Google): {end_formatted}")
            
            # Подготавливаем участников
            attendee_list = []
            if attendees:
                for email in attendees:
                    attendee_list.append({'email': email})
            
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': start_formatted,
                'end': end_formatted,
            }
            
            if attendee_list:
                event['attendees'] = attendee_list
            
            created_event = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event
            ).execute()
            
            print(f"   ✅ Событие создано в Google Calendar: {created_event.get('id')}")
            
            return {
                'id': created_event['id'],
                'summary': created_event['summary'],
                'description': created_event.get('description', ''),
                'start': created_event['start'].get('dateTime', created_event['start'].get('date')),
                'end': created_event['end'].get('dateTime', created_event['end'].get('date')),
                'readable_start': self._format_readable_datetime(
                    created_event['start'].get('dateTime', created_event['start'].get('date'))
                ),
                'readable_end': self._format_readable_datetime(
                    created_event['end'].get('dateTime', created_event['end'].get('date'))
                ),
                'duration': self._get_event_duration(
                    created_event['start'].get('dateTime', created_event['start'].get('date')),
                    created_event['end'].get('dateTime', created_event['end'].get('date'))
                ),
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
                tz = event['start'].get('timeZone', TIMEZONE)
                if 'T' in start_time:
                    event['start'] = {'dateTime': start_time.rstrip('Z'), 'timeZone': tz}
                else:
                    event['start'] = {'date': start_time}

            if end_time is not None:
                tz = event['end'].get('timeZone', TIMEZONE)
                if 'T' in end_time:
                    event['end'] = {'dateTime': end_time.rstrip('Z'), 'timeZone': tz}
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
                'readable_start': self._format_readable_datetime(
                    updated_event['start'].get('dateTime', updated_event['start'].get('date'))
                ),
                'readable_end': self._format_readable_datetime(
                    updated_event['end'].get('dateTime', updated_event['end'].get('date'))
                ),
                'duration': self._get_event_duration(
                    updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                    updated_event['end'].get('dateTime', updated_event['end'].get('date'))
                ),
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
            
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            end_time = event['end'].get('dateTime', event['end'].get('date'))
            
            return {
                'id': event.get('id'),
                'summary': event.get('summary', ''),
                'description': event.get('description', ''),
                'start': start_time,
                'end': end_time,
                'readable_start': self._format_readable_datetime(start_time),
                'readable_end': self._format_readable_datetime(end_time),
                'duration': self._get_event_duration(start_time, end_time),
                'time_to_event': self._get_time_to_event(start_time),
                'location': event.get('location', ''),
                'status': event.get('status'),
                'htmlLink': event.get('htmlLink'),
                'attendee_count': len(event.get('attendees', [])) if event.get('attendees') else 0
            }
            
        except HttpError as error:
            raise Exception(f"Ошибка при получении события: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    # ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========
    
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
                    start_dt = self._parse_datetime(start)
                    end_dt = self._parse_datetime(end)
                    if start_dt and end_dt:
                        busy_slots.append((start_dt, end_dt))
            
            # Находим свободные слоты
            free_slots = []
            
            # Создаем datetime для начала и конца поиска
            from datetime import timezone
            current_time = datetime.strptime(f"{date}T{start_hour:02d}:00:00", "%Y-%m-%dT%H:%M:%S")
            current_time = current_time.replace(tzinfo=timezone.utc)
            
            end_time = datetime.strptime(f"{date}T{end_hour:02d}:00:00", "%Y-%m-%dT%H:%M:%S")
            end_time = end_time.replace(tzinfo=timezone.utc)
            
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
                        'start': current_time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        'end': slot_end.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        'readable_start': self._format_readable_datetime(current_time.strftime('%Y-%m-%dT%H:%M:%S%z')),
                        'readable_end': self._format_readable_datetime(slot_end.strftime('%Y-%m-%dT%H:%M:%S%z'))
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
            formatted_events = []
            for e in events:
                start_time = e['start'].get('dateTime', e['start'].get('date'))
                end_time = e['end'].get('dateTime', e['end'].get('date'))
                
                event_data = {
                    'id': e.get('id'),
                    'summary': e.get('summary', ''),
                    'start': start_time,
                    'end': end_time,
                    'readable_start': self._format_readable_datetime(start_time),
                    'readable_end': self._format_readable_datetime(end_time),
                    'duration': self._get_event_duration(start_time, end_time),
                    'time_to_event': self._get_time_to_event(start_time),
                    'description': e.get('description', '')
                }
                formatted_events.append(event_data)
            return formatted_events
            
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
            
            from datetime import timezone
            
            now = datetime.now(timezone.utc)
            
            # Если hours > 24, преобразуем в дни
            if hours <= 24:
                time_min = now.isoformat()
                time_max = (now + timedelta(hours=hours)).isoformat()
            else:
                days = hours // 24
                time_min = now.isoformat()
                time_max = (now + timedelta(days=days)).isoformat()
            
            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for e in events:
                start_time = e['start'].get('dateTime', e['start'].get('date'))
                end_time = e['end'].get('dateTime', e['end'].get('date'))
                
                event_data = {
                    'id': e.get('id'),
                    'summary': e.get('summary', 'Без названия'),
                    'start': start_time,
                    'end': end_time,
                    'readable_start': self._format_readable_datetime(start_time),
                    'readable_end': self._format_readable_datetime(end_time),
                    'time_to_event': self._get_time_to_event(start_time),
                    'duration': self._get_event_duration(start_time, end_time),
                    'description': e.get('description', ''),
                    'location': e.get('location', ''),
                    'status': e.get('status', 'confirmed'),
                    'creator': e.get('creator', {}).get('email', ''),
                    'attendee_count': len(e.get('attendees', [])) if e.get('attendees') else 0
                }
                formatted_events.append(event_data)
            
            return formatted_events
            
        except HttpError as error:
            raise Exception(f"Ошибка при получении ближайших событий: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")
    
    async def get_calendar_summary(self) -> Dict:
        """
        Получить краткую статистику по календарю пользователя
        """
        try:
            from datetime import timezone
            
            now_utc = datetime.now(timezone.utc)
            
            # Сегодня в UTC
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1) - timedelta(seconds=1)
            
            # Завтра в UTC
            tomorrow_start = today_start + timedelta(days=1)
            tomorrow_end = tomorrow_start + timedelta(days=1) - timedelta(seconds=1)
            
            # Получаем события на сегодня
            today_events = await self.get_events(
                time_min=today_start.isoformat(),
                time_max=today_end.isoformat()
            )
            
            # Получаем события на завтра
            tomorrow_events = await self.get_events(
                time_min=tomorrow_start.isoformat(),
                time_max=tomorrow_end.isoformat()
            )
            
            # Получаем ближайшие события (следующие 24 часа)
            upcoming = await self.get_upcoming_events(hours=24)
            
            next_event = None
            if upcoming:
                next_event = {
                    'summary': upcoming[0].get('summary', 'Без названия'),
                    'time': upcoming[0].get('readable_start', ''),
                    'time_to_event': upcoming[0].get('time_to_event', '')
                }
            
            return {
                'today_events_count': len(today_events),
                'tomorrow_events_count': len(tomorrow_events),
                'next_24h_events_count': len(upcoming),
                'next_event': next_event
            }
            
        except Exception as e:
            raise Exception(f"Ошибка при получении статистики: {e}")


    async def get_free_blocks(self, date: str) -> List[Dict]:
        """
        Найти свободные промежутки времени за весь день (00:00–24:00).

        Возвращает пустой список если весь день свободен,
        иначе — список промежутков между событиями.
        """
        try:
            service = await self._get_service()

            time_min = f"{date}T00:00:00Z"
            time_max = f"{date}T23:59:59Z"

            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])

            from datetime import timezone

            day_start = datetime.strptime(f"{date}T00:00:00", "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            day_end   = datetime.strptime(f"{date}T23:59:59", "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

            # Собираем занятые интервалы (только timed events, не all-day)
            busy: List[tuple] = []
            for event in events:
                raw_start = event["start"].get("dateTime")
                raw_end   = event["end"].get("dateTime")
                if not raw_start or not raw_end:
                    # all-day event → весь день занят
                    return []
                s = self._parse_datetime(raw_start)
                e = self._parse_datetime(raw_end)
                if s and e:
                    busy.append((s, e))

            if not busy:
                # Нет событий — весь день свободен
                return []

            # Сортируем и мёрджим перекрывающиеся интервалы
            busy.sort(key=lambda x: x[0])
            merged: List[tuple] = []
            cs, ce = busy[0]
            for s, e in busy[1:]:
                if s <= ce:
                    ce = max(ce, e)
                else:
                    merged.append((cs, ce))
                    cs, ce = s, e
            merged.append((cs, ce))

            # Вычисляем свободные промежутки
            free_blocks = []
            cursor = day_start

            for bs, be in merged:
                if cursor < bs:
                    free_blocks.append({
                        "start": cursor.strftime("%H:%M"),
                        "end":   bs.strftime("%H:%M"),
                    })
                cursor = max(cursor, be)

            if cursor < day_end:
                free_blocks.append({
                    "start": cursor.strftime("%H:%M"),
                    "end":   "24:00",
                })

            return free_blocks

        except HttpError as error:
            raise Exception(f"Ошибка при получении свободных блоков: {error}")
        except Exception as e:
            raise Exception(f"Ошибка сервиса: {e}")


# Фабрика для создания сервиса
def get_calendar_service(telegram_user_id: str, session: AsyncSession) -> GoogleCalendarService:
    """Создать сервис календаря для пользователя"""
    return GoogleCalendarService(telegram_user_id, session)