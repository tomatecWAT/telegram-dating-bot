# bot.py
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, require_bot_token
from database import init_db
from handlers import router
from aiogram.types import BotCommand


async def set_commands(bot):
    commands = [
        BotCommand(command="myprofile", description="📄 Моя анкета"),
        BotCommand(command="editprofile", description="✏️ Редактировать анкету"),
        BotCommand(command="resetprofile", description="🔄 Заполнить анкету заново"),
        BotCommand(command="view", description="👀 Смотреть анкеты"),
    ]
    await bot.set_my_commands(commands)

async def main():
    # ensure token is present
    require_bot_token()

    # создаём таблицы
    init_db()

    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # подключаем роутер
    dp.include_router(router)

    print("Бот запущен. Ctrl+C для остановки.")
    try:
        await set_commands(bot)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())


