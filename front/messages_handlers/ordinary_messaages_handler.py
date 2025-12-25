from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command
from controllers.async_db_controller import AsyncPostgres
from keyboards.reply_keyboards import command_keyboard

simple_router = Router()

@simple_router.message(CommandStart())
async def command_start_handler(message: Message, db: AsyncPostgres) -> None:
    await db.add_user(message.from_user.id, message.from_user.username)
    await message.answer("Привет. Я умный органайзер твоих мыслей и планов", reply_markup=command_keyboard())

@simple_router.message(Command("help"))
async def command_start_handler(message: Message, db: AsyncPostgres) -> None:
    await db.add_user(message.from_user.id, message.from_user.username)
    msg = """\n🔥<b>Возможности бота:</b> 🔥

/create_note: создание заметки, в которой могут храниться планы и мысли разных категорий
/add_thoughts: нахождение планов и мыслей из голового сообщения
/delete_note: удаление заметки
/get_note:  получение планов и мыслей у одной заметки, а  также ее редактирование
/get_notes: получение списка всех заметок в форме 'ID - Название'
/help: описание всех команд"""
    await message.answer(msg, reply_markup=command_keyboard(), parse_mode="html")


