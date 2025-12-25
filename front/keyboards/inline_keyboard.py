from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import Optional, List
import json

class CallbackParametrs(CallbackData, prefix = "fabnum"):
    action:str
    value: Optional[str] = None
    thoughts: Optional[str] = None
    thought: Optional[dict] = None

def delete_thoughts_keyboard(includings: List[tuple]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    incl = json.dumps(includings, ensure_ascii=True)
    builder.add(InlineKeyboardButton(text = "Режим удаления", callback_data=CallbackParametrs(action="delete_note_thought", value = incl).pack()))
    return builder

def choose_category_keyboard(includings) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    buttons = []
    includings = json.loads(includings)
    for category, thoughts in includings:
        thou= json.dumps(thoughts)
        buttons.append(InlineKeyboardButton(text=category,
                                            callback_data=CallbackParametrs(action="choose_category", thoughts=thou).pack()))
    builder.add(buttons)
    return builder

def choose_id_keyboard(thoughts) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    buttons= []
    thoughts = json.loads(thoughts)
    for i  in range (len(thoughts)):
        thou = thoughts[i]
        buttons.append(InlineKeyboardButton(text = thou.content, callback_data=CallbackParametrs(action="choose_id", thought= thou).pack() ))
    builder.add(buttons)

    return builder