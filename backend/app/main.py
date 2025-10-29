import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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

from NLP_engine.text_to_speech import tts_engine
from fastapi.responses import FileResponse

app = FastAPI(
    title="AI-Planner API",
    description="AI-Powered Scheduling Assistant with Optional Voice Features",
    version="2.2.0",
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
    enable_tts: bool = Field(False, description="Включить озвучку подтверждения")

class ScheduleResponse(BaseModel):
    event_id: str
    scheduled_time: str
    event_type: str
    title: str
    message: str
    tts_used: bool

class VoiceScheduleRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    calendar_type: str = Field("apple", description="Тип календаря")
    enable_tts: bool = Field(False, description="Включить озвучку ответа")

class VoiceScheduleResponse(BaseModel):
    original_audio_text: str
    scheduled_event: ScheduleResponse
    message: str

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

class TTSRequest(BaseModel):
    text: str = Field(..., description="Текст для озвучивания")
    user_id: str = Field(..., description="ID пользователя")

class TTSResponse(BaseModel):
    message: str
    text_length: int
    audio_url: Optional[str] = None

class DailySummaryRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    enable_tts: bool = Field(False, description="Включить озвучку сводки")

# ===== TEXT PARSING =====
def parse_schedule_text(text: str) -> dict:
    text_lower = text.lower()
    
    event_time = datetime.now() + timedelta(hours=2)
    if "завтра" in text_lower:
        event_time = datetime.now() + timedelta(days=1)
    elif "сегодня" in text_lower:
        event_time = datetime.now()
    
    event_type = "meeting"
    if any(word in text_lower for word in ["тренировка", "спорт", "зал"]):
        event_type = "workout"
    elif any(word in text_lower for word in ["обед", "ужин", "еда"]):
        event_type = "meal"
    elif any(word in text_lower for word in ["встреча", "совещание"]):
        event_type = "meeting"
    
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
        "message": "AI-Planner API v2.2", 
        "description": "AI-Powered Scheduling with Optional Voice Features",
        "version": "2.2.0",
        "features": ["speech-to-text", "google-tts", "nlp-parsing", "scheduling"],
        "tts_behavior": "optional - use enable_tts parameter to control voice",
        "endpoints": {
            "health": "GET /health",
            "schedule_text": "POST /v1/schedule", 
            "schedule_voice": "POST /v1/voice/schedule",
            "tts_speak": "POST /v1/tts/speak",
            "tts_generate": "POST /v1/tts/generate",
            "daily_summary": "POST /v1/tts/daily-summary",
            "get_events": "GET /v1/events/{user_id}",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="2.2.0",
        timestamp=datetime.now().isoformat()
    )

@app.post("/v1/schedule", response_model=ScheduleResponse)
async def schedule_event(request: ScheduleRequest):
    """Планирование события с опциональной озвучкой"""
    parsed_event = parse_schedule_text(request.text)
    
    tts_used = False
    if request.enable_tts:
        confirmation_text = f"Добавлено: {parsed_event['title']}"
        tts_engine.speak(confirmation_text)
        tts_used = True
    
    return ScheduleResponse(
        event_id=parsed_event["event_id"],
        scheduled_time=parsed_event["scheduled_time"],
        event_type=parsed_event["event_type"],
        title=parsed_event["title"],
        message="Событие успешно запланировано",
        tts_used=tts_used
    )

@app.post("/v1/voice/schedule", response_model=VoiceScheduleResponse)
async def schedule_from_voice(
    audio: UploadFile = File(...),
    user_id: str = Form(...),
    calendar_type: str = Form("apple"),
    enable_tts: bool = Form(False)
):
    """Планирование через голос с опциональной озвучкой ответа"""
    try:
        if not audio.content_type.startswith('audio/'):
            raise HTTPException(400, "Файл должен быть аудио")
        
        audio_bytes = await audio.read()
        
        if len(audio_bytes) == 0:
            raise HTTPException(400, "Аудиофайл пустой")
        
        text_request = speech_recognizer.transcribe_audio_bytes(audio_bytes)
        
        if not text_request.strip():
            raise HTTPException(400, "Не удалось распознать речь")
        
        parsed_event = parse_schedule_text(text_request)
        
        tts_used = False
        if enable_tts:
            voice_response = f"Добавлено: {parsed_event['title']}"
            tts_engine.speak(voice_response)
            tts_used = True
        
        scheduled_event = ScheduleResponse(
            event_id=parsed_event["event_id"],
            scheduled_time=parsed_event["scheduled_time"],
            event_type=parsed_event["event_type"],
            title=parsed_event["title"],
            message="Событие добавлено через голосовой запрос",
            tts_used=tts_used
        )
        
        return VoiceScheduleResponse(
            original_audio_text=text_request,
            scheduled_event=scheduled_event,
            message="Голосовой запрос успешно обработан"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.get("/v1/events/{user_id}")
async def get_user_events(user_id: str, date: Optional[str] = None, enable_tts: bool = False):
    """Получение событий пользователя с опциональной озвучкой"""
    mock_events = [
        {
            "event_id": f"event_{user_id}_1",
            "title": "Совещание",
            "time": datetime.now().replace(hour=10, minute=0, second=0).isoformat(),
            "type": "meeting"
        },
        {
            "event_id": f"event_{user_id}_2", 
            "title": "Тренировка",
            "time": datetime.now().replace(hour=18, minute=0, second=0).isoformat(),
            "type": "workout"
        }
    ]
    
    tts_used = False
    if enable_tts:
        events_count = len(mock_events)
        tts_text = f"Событий: {events_count}"
        tts_engine.speak(tts_text)
        tts_used = True
    
    return {
        "user_id": user_id,
        "date": date or datetime.now().date().isoformat(),
        "events": mock_events,
        "events_count": len(mock_events),
        "tts_used": tts_used
    }

@app.post("/v1/tts/speak", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Явное озвучивание текста (всегда работает)"""
    success = tts_engine.speak(request.text)
    
    if success:
        return TTSResponse(
            message="Текст успешно озвучен",
            text_length=len(request.text),
            audio_url=None
        )
    else:
        raise HTTPException(status_code=500, detail="Ошибка озвучивания текста")

@app.post("/v1/tts/generate", response_model=TTSResponse)
async def generate_speech_audio(request: TTSRequest):
    """Генерация аудио файла из текста"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
        
        success = tts_engine.save_to_file(request.text, temp_path)
        
        if success and os.path.exists(temp_path):
            filename = os.path.basename(temp_path)
            return TTSResponse(
                message="Аудио файл сгенерирован",
                text_length=len(request.text),
                audio_url=f"/v1/tts/download/{filename}"
            )
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(status_code=500, detail="Не удалось сгенерировать аудио")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.get("/v1/tts/download/{filename}")
async def download_audio(filename: str):
    """Скачивание сгенерированного аудио файла"""
    file_path = os.path.join(tempfile.gettempdir(), filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Аудио файл не найден")
    
    return FileResponse(
        path=file_path,
        media_type='audio/mpeg',
        filename=f"ai_planner_{filename}"
    )

@app.post("/v1/tts/daily-summary")
async def speak_daily_summary(request: DailySummaryRequest):
    """Озвучивание сводки на день с опциональной озвучкой"""
    try:
        events_response = await get_user_events(request.user_id)
        events = events_response["events"]
        
        summary_text = ""
        if not events:
            summary_text = "Событий нет"
        else:
            summary_text = f"Событий: {len(events)}"
        
        tts_used = False
        if request.enable_tts:
            success = tts_engine.speak(summary_text)
            tts_used = success
        
        return {
            "message": "Ежедневная сводка сгенерирована",
            "user_id": request.user_id,
            "events_count": len(events),
            "summary_text": summary_text,
            "tts_used": tts_used
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания сводки: {str(e)}")

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