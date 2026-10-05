import asyncio
import logging
import sys
import os

# Принудительно задаем корень проекта для корректных импортов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import handlers  # Импортируем напрямую модуль
from config import TELEGRAM_BOT_TOKEN

async def main():
    logging.basicConfig(level=logging.INFO)

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN. Укажите токен в файле .env.")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(handlers.router)
    
    await bot.set_my_commands([
        BotCommand(command="start", description="Направления обучения СПбГУ")
    ])
    
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())