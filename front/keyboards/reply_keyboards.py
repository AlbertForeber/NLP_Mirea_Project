from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

def command_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="/get_note"),
        KeyboardButton(text="/get_notes")
    )

    builder.row(
        KeyboardButton(text="/add_thoughts")
    )
    builder.row(

        KeyboardButton(text="/create_note"),
        KeyboardButton(text="/delete_note")
    )
    builder.row(
        KeyboardButton(text="/categories")
    )

    return builder.as_markup(resize_keyboard=True)