import os
from dotenv import load_dotenv

load_dotenv()

# Google OAuth
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
SCOPE = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.profile"

# Настройки календаря
CALENDAR_ID = "primary"
TIMEZONE = "Europe/Moscow"