import random
import string
import time
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
import whisper
import tempfile
import os

app = FastAPI(
    title="AI-Planner API",
    description="AI-Powered Scheduling Assistant with Voice Recognition",
    version="1.0.0",
)

# ===== SPEECH RECOGNITION =====
class SpeechRecognizer:
    def __init__(self, model_size: str = "base"):
        self.model = whisper.load_model(model_size)
    
    def transcribe_audio_bytes(self, audio_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            result = self.model.transcribe(temp_path, language='ru')
            os.unlink(temp_path)
            return result["text"]
        except Exception as e:
            raise Exception(f"Ошибка транскрибации: {e}")

speech_recognizer = SpeechRecognizer()

# ===== MODELS =====
class ScheduleRequest(BaseModel):
    text: str = Field(..., description="Текст запроса")
    user_id: str = Field(..., description="ID пользователя")
    calendar_type: str = Field("apple", description="Тип календаря")

class ScheduleResponse(BaseModel):
    event_id: str
    scheduled_time: str
    event_type: str
    title: str
    message: str

class VoiceScheduleResponse(BaseModel):
    original_audio_text: str
    scheduled_event: ScheduleResponse
    message: str

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

# ===== TEXT PARSING =====
def parse_schedule_text(text: str) -> dict:
    text_lower = text.lower()
    
    # Определение времени
    event_time = datetime.now() + timedelta(hours=2)
    if "завтра" in text_lower:
        event_time = datetime.now() + timedelta(days=1)
    elif "сегодня" in text_lower:
        event_time = datetime.now()
    
    # Определение типа события
    event_type = "meeting"
    if any(word in text_lower for word in ["тренировка", "спорт", "зал"]):
        event_type = "workout"
    elif any(word in text_lower for word in ["обед", "ужин", "еда"]):
        event_type = "meal"
    
    return {
        "event_id": f"event_{int(time.time())}_{random.randint(1000, 9999)}",
        "event_type": event_type,
        "scheduled_time": event_time.isoformat(),
        "title": text[:50]
    }

# ===== API ENDPOINTS =====
@app.get("/")
async def root():
    return {
        "message": "AI-Planner API", 
        "description": "AI-Powered Scheduling Assistant",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

@app.post("/v1/schedule", response_model=ScheduleResponse)
async def schedule_event(request: ScheduleRequest):
    parsed_event = parse_schedule_text(request.text)
    
    return ScheduleResponse(
        event_id=parsed_event["event_id"],
        scheduled_time=parsed_event["scheduled_time"],
        event_type=parsed_event["event_type"],
        title=parsed_event["title"],
        message="Событие успешно запланировано в AI-Planner"
    )

@app.post("/v1/voice/schedule", response_model=VoiceScheduleResponse)
async def schedule_from_voice(
    audio: UploadFile = File(...),
    user_id: str = Form(...),
    calendar_type: str = Form("apple")
):
    try:
        if not audio.content_type.startswith('audio/'):
            raise HTTPException(400, "Файл должен быть аудио")
        
        audio_bytes = await audio.read()
        
        if len(audio_bytes) == 0:
            raise HTTPException(400, "Аудиофайл пустой")
        
        # Преобразуем голос в текст
        text_request = speech_recognizer.transcribe_audio_bytes(audio_bytes)
        
        if not text_request.strip():
            raise HTTPException(400, "AI-Planner не смог распознать речь")
        
        # Парсинг текста и создание события
        parsed_event = parse_schedule_text(text_request)
        
        scheduled_event = ScheduleResponse(
            event_id=parsed_event["event_id"],
            scheduled_time=parsed_event["scheduled_time"],
            event_type=parsed_event["event_type"],
            title=parsed_event["title"],
            message="Событие добавлено через голосовой запрос в AI-Planner"
        )
        
        return VoiceScheduleResponse(
            original_audio_text=text_request,
            scheduled_event=scheduled_event,
            message="Голосовой запрос успешно обработан AI-Planner"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка AI-Planner: {str(e)}")

@app.get("/v1/events/{user_id}")
async def get_user_events(user_id: str, date: Optional[str] = None):
    mock_events = [
        {
            "event_id": f"event_{user_id}_1",
            "title": "Еженедельное совещание AI-Planner",
            "time": "2024-01-15T10:00:00",
            "type": "meeting"
        },
        {
            "event_id": f"event_{user_id}_2", 
            "title": "Тренировка - запланировано AI-Planner",
            "time": "2024-01-15T18:00:00",
            "type": "workout"
        }
    ]
    
    return {
        "user_id": user_id,
        "date": date or datetime.now().date().isoformat(),
        "events": mock_events,
        "source": "AI-Planner API"
    }

# Обработчик ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": {
            "message": f"AI-Planner Error: {exc.detail}",
            "type": "ai_planner_error",
            "code": exc.status_code
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)