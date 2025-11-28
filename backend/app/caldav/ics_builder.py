from icalendar import Calendar, Event
from datetime import datetime
import pytz
from uuid import uuid4


def build_ics_calendar(token: str, events: list[dict]) -> str:
    cal = Calendar()
    cal.add('prodid', '-//PlannerAI//EN')
    cal.add('version', '2.0')

    for ev in events:
        event = Event()

        event.add('uid', f"{ev['uid']}@plannerai")
        event.add('summary', ev['title'])

        # Преобразуем строки в datetime
        start_dt = datetime.fromisoformat(ev['start'])
        end_dt = datetime.fromisoformat(ev['end'])

        # iOS любит Z или timezone-aware время
        start_dt = start_dt.astimezone(pytz.UTC)
        end_dt = end_dt.astimezone(pytz.UTC)

        event.add('dtstart', start_dt)
        event.add('dtend', end_dt)
        event.add('dtstamp', datetime.utcnow().replace(tzinfo=pytz.UTC))

        cal.add_component(event)

    # Генерируем ICS как bytes → декодируем в str
    return cal.to_ical().decode('utf-8')