from datetime import datetime

def build_ics_calendar(token: str, events: list[dict]) -> str:
    """
    Формирует корректный ICS-календарь (iCalendar v2.0).
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PlannerAI//EN",
    ]

    for ev in events:
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{ev['uid']}@plannerai",
            f"DTSTAMP:{_dtstamp()}",
            f"DTSTART:{_to_ical_datetime(ev['start'])}",
            f"DTEND:{_to_ical_datetime(ev['end'])}",
            f"SUMMARY:{ev['title']}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    return "\r\n".join(lines)

def _dtstamp() -> str:
    """
    Текущее время в формате 20250101T123000Z
    """
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def _to_ical_datetime(dt_str: str) -> str:
    """
    Конвертация ISO8601 → формат iCalendar.
    Пример:
    2025-11-30T18:00:00+03:00 → 20251130T180000+0300
    """

    # Разделяем дату и время
    date, time = dt_str.split("T")
    yyyy, mm, dd = date.split("-")

    # Разделяем часы/минуты/секунды и offset
    if "+" in time:
        clock, offset = time.split("+")
        sign = "+"
    elif "-" in time[1:]:  # если отрицательный offset
        clock, offset = time.split("-", 1)
        sign = "-"
    else:
        # без offset — считаем UTC
        clock = time
        offset = "0000"
        sign = "+"

    hh, mi, ss = clock.split(":")

    offset = offset.replace(":", "")  # "03:00" → "0300"

    return f"{yyyy}{mm}{dd}T{hh}{mi}{ss}{sign}{offset}"