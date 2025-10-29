from gtts import gTTS
import pygame
import io
import os
import threading

class GoogleTTS:
    def __init__(self):
        pygame.mixer.init()
        self.is_speaking = False
        print("Google TTS инициализирован")
    
    def speak(self, text: str) -> bool:
        """Озвучивание текста с Google TTS"""
        if self.is_speaking:
            return False
            
        try:
            self.is_speaking = True
            
            # Создаем аудио в памяти
            tts = gTTS(text=text, lang='ru', slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            # Воспроизводим в отдельном потоке
            def play_audio():
                pygame.mixer.music.load(fp)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                self.is_speaking = False
            
            thread = threading.Thread(target=play_audio)
            thread.daemon = True
            thread.start()
            
            return True
            
        except Exception as e:
            print(f"Ошибка Google TTS: {e}")
            self.is_speaking = False
            return False
    
    def save_to_file(self, text: str, filename: str) -> bool:
        """Сохранение аудио в файл"""
        try:
            tts = gTTS(text=text, lang='ru', slow=False)
            tts.save(filename)
            return os.path.exists(filename)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return False

# Глобальный экземпляр
tts_engine = GoogleTTS()