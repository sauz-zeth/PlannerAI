from aiogram import Dispatcher
from .handlers import router

def setup(dp: Dispatcher):
    dp.include_router(router)