from aiogram import Router, F, types
from .backend_client import send_to_agent
from .whisper_engine import transcribe_voice

router = Router()

@router.message(F.voice)
async def handle_voice(msg: types.Message):
    await msg.answer("🎙 Распознаю голосовое сообщение...")

    file = await msg.bot.get_file(msg.voice.file_id)
    buffer = await msg.bot.download_file(file.file_path)
    text = await transcribe_voice(buffer.getvalue())
    
    agent_reply = await send_to_agent(text, msg.date)
    await msg.answer(f"📝 {text}\n\n{agent_reply}")


@router.message(F.text)
async def handle_text(msg: types.Message):
    reply = await send_to_agent(msg.text, msg.date)
    await msg.answer(reply)