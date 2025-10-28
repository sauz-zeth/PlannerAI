import whisper
from typing import Optional
import tempfile
import os

class SpeechRecognizer:
    def __init__(self, model_size: str = "base"):
        """Инициализация распознавателя речи для AI-Planner"""
        self.model = whisper.load_model(model_size)
    
    def transcribe_audio_file(self, audio_path: str) -> str:
        """Транскрибация аудиофайла в текст для AI-Planner"""
        try:
            result = self.model.transcribe(audio_path, language='ru')
            return result["text"]
        except Exception as e:
            raise Exception(f"AI-Planner Speech Recognition Error: {e}")
    
    def transcribe_audio_bytes(self, audio_bytes: bytes) -> str:
        """Транскрибация аудио из bytes для AI-Planner API"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            result = self.model.transcribe(temp_path, language='ru')
            os.unlink(temp_path)
            return result["text"]
        except Exception as e:
            raise Exception(f"AI-Planner Speech Recognition Error: {e}")

# Глобальный экземпляр для AI-Planner
speech_recognizer = SpeechRecognizer()