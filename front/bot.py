from aiogram import Bot, Dispatcher, html, Router
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
from middleware import DatabaseMiddleware
#from dotenv import load_dotenv


from messages_handlers.fsm_messages import fsm_router
from messages_handlers.ordinary_messaages_handler import simple_router
from controllers.async_db_controller import AsyncPostgres
import os

#load_dotenv()
#TOKEN = "8119060681:AAFt0-AiNxUVihxhaSrBOBGU_ijST4nTSkY"

TOKEN = os.getenv("BOT_TOKEN")
dp = Dispatcher()
pos = AsyncPostgres()


async def main() -> None:
    bot = Bot(TOKEN)
    await dp.start_polling(bot )

@dp.startup()
async def on_startup():
    await pos.connect()
    fsm_router.message.middleware(DatabaseMiddleware(pos))
    simple_router.message.middleware(DatabaseMiddleware(pos))
    dp.include_router(fsm_router)
    dp.include_router(simple_router)
    print("Bot is working")


if __name__ == "__main__":

    asyncio.run(main())

