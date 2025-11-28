from uuid import uuid4

# token -> список событий
EVENTS: dict[str, list[dict]] = {}

def add_event(token: str, title: str, start: str, end: str) -> dict:
    """
    Добавляет событие в память. Пока без БД.
    Возвращает добавленное событие.
    """
    uid = str(uuid4())

    event = {
        "uid": uid,
        "title": title,
        "start": start,
        "end": end,
    }

    # Создаём список событий для конкретного пользователя
    EVENTS.setdefault(token, []).append(event)

    return event


def get_events(token: str) -> list[dict]:
    """
    Возвращает список всех событий пользователя.
    Если нет таких — пустой список.
    """
    return EVENTS.get(token, [])