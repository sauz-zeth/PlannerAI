"""
Tool definitions for calendar agent.
LLM sees ONLY this file.
"""

calendar_tools = [

    # ================== GET EVENTS ==================
    {
        "type": "function",
        "function": {
            "name": "get_events",
            "description": "Получить события пользователя из календаря",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Максимальное количество событий",
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Начальная дата/время в ISO формате",
                    },
                    "time_max": {
                        "type": "string",
                        "description": "Конечная дата/время в ISO формате",
                    },
                },
            },
        },
    },

    # ================== CREATE EVENT ==================
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Создать новое событие в календаре пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Название события",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Время начала в ISO формате",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Время окончания в ISO формате",
                    },
                    "description": {
                        "type": "string",
                        "description": "Описание события",
                    },
                    "location": {
                        "type": "string",
                        "description": "Место проведения",
                    },
                },
                "required": ["summary", "start_time", "end_time"],
            },
        },
    },

    # ================== UPDATE EVENT ==================
    {
        "type": "function",
        "function": {
            "name": "update_event",
            "description": "Обновить существующее событие в календаре",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "ID события",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Новое название события",
                    },
                    "description": {
                        "type": "string",
                        "description": "Новое описание события",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Новое время начала в ISO формате",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Новое время окончания в ISO формате",
                    },
                    "location": {
                        "type": "string",
                        "description": "Новое место проведения",
                    },
                },
                "required": ["event_id"],
            },
        },
    },

    # ================== DELETE EVENT ==================
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "Удалить событие пользователя из календаря",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "ID события",
                    },
                },
                "required": ["event_id"],
            },
        },
    },

    # ================== FIND FREE SLOTS ==================
    {
        "type": "function",
        "function": {
            "name": "find_free_slots",
            "description": "Найти свободные временные слоты в календаре пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Дата в формате YYYY-MM-DD",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Длительность слота в минутах",
                        "minimum": 1,
                        "maximum": 1440,
                    },
                    "start_hour": {
                        "type": "integer",
                        "description": "Начальный час дня (0–23)",
                        "minimum": 0,
                        "maximum": 23,
                    },
                    "end_hour": {
                        "type": "integer",
                        "description": "Конечный час дня (0–23)",
                        "minimum": 0,
                        "maximum": 23,
                    },
                },
                "required": ["date"],
            },
        },
    },

    # ================== SEARCH EVENTS ==================
    {
        "type": "function",
        "function": {
            "name": "search_events",
            "description": "Поиск событий пользователя по тексту",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Текст для поиска",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Максимальное количество результатов",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
            },
        },
    },

    # ================== UPCOMING EVENTS ==================
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_events",
            "description": "Получить ближайшие события пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Количество часов вперед",
                        "minimum": 1,
                        "maximum": 168,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Максимальное количество событий",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        },
    },

    # ================== CALENDAR SUMMARY ==================
    {
        "type": "function",
        "function": {
            "name": "get_calendar_summary",
            "description": "Получить краткую статистику по календарю пользователя",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]