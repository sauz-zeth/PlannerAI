import tempfile
import asyncio
from io import BytesIO
import whisper

_model = whisper.load_model("base")

async def transcribe_voice(file_bytes: bytes) -> str:
    def _task():
        with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            res = _model.transcribe(tmp.name, language="ru")
        return res.get("text", "").strip()

    return await asyncio.to_thread(_task)