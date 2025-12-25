from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.filters.state import State, StatesGroup
from controllers.async_db_controller import AsyncPostgres
from typing import Dict, List
from collections import defaultdict
from controllers.agent_controller import MlController
from keyboards.inline_keyboard import delete_thoughts_keyboard, CallbackParametrs, choose_category_keyboard, choose_id_keyboard

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram import F
from aiogram import Bot
from aiogram.enums import ChatAction
import io
from aiogram.types import BufferedInputFile
import json

agent_controller = MlController()
fsm_router = Router()

class CreateNoteState(StatesGroup):
    name = State()

class GetNoteCategories(StatesGroup):
    name = State()

class GetNoteIncludings(StatesGroup):
    name = State()

class DeleteNote(StatesGroup):
    note_id = State()

class AddThought(StatesGroup):
    note_id = State()
    note = State()

class GetAudio(StatesGroup):
    note_id = State()

#-------------------------------------------------
#создание заметки - наименования -> бд
@fsm_router.message(Command("create_note"))
async def command_create_note_handler(message: Message, state: FSMContext,db) -> None:
    await message.answer("Отправьте название будущей заметки")
    await state.set_state(CreateNoteState.name)


@fsm_router.message(CreateNoteState.name)
async def command_create_note_handler_name(message: Message, state: FSMContext,db: AsyncPostgres) -> None:
    name = message.text
    resault = await db.add_new_note(message.from_user.id, name)
    await message.answer(text="Добавлено!")
    await state.clear()

#----------------------------------------------------------------------------------------------
#удаление заметки - вывод наименвоаний ввдеите индекс
@fsm_router.message(Command("delete_note"))
async def command_delete_note_handler(message: Message, db: AsyncPostgres, state: FSMContext) -> None:
    all_notes = await db.get_all_notes(message.from_user.id)
    if not all_notes:
        await message.answer("У вас пока нет записей")
        return

    all_notes_dict:Dict = defaultdict()
    text_message = ""
    for i in range(len( all_notes)):
        note = all_notes[i]
        all_notes_dict[i] = note
        text_message += f"{i} - {note.get("note_name")}\n"
    text_message = text_message[:-1]

    await state.set_state(DeleteNote.note_id)
    await state.update_data(all_notes=all_notes_dict)
    await message.answer("Выберите id заметки для удаления")
    await message.answer(text_message)


#pg and agent
@fsm_router.message(DeleteNote.note_id)
async def command_delete_note_id_stage_handler(message: Message, db: AsyncPostgres, state: FSMContext) -> None:
    state_data: Dict = await state.get_data()
    all_notes:Dict = state_data.get("all_notes")
    note_id = message.text

    if (note_id.isdigit() and int(note_id) in list(all_notes.keys())):
        note_id = int(note_id)
        note_ = all_notes[note_id].get("note_id")
        try:
            reuslt_agent = await agent_controller.delete_note(message.from_user.id, note_)
            print("Результат удаления с агента ", reuslt_agent)
            await message.answer("Удаление выполнено успешно")
        except Exception as e:
            #logging
            print("Problem in deleting " + str(e))
            await message.answer("Попробуйте чуть позже")
        await state.clear()

    elif (note_id.isdigit()):
        await message.reply("Данное id не является корректным")

    elif note_id == "/get_notes":
        await state.clear()
        await  command_get_notes_handler(message, db)
    elif note_id == "/get_note":
        await state.clear()
        await command_get_note_handler(message, state ,  db)

    elif note_id == "/create_note":
        await state.clear()
        await command_create_note_handler(message, state ,  db)

    elif note_id == "/categories":
        await state.clear()
        await command_categories_handler(message ,state , db)

    elif note_id == "/add_thoughts":
        await state.clear()
        await command_add_note_handler(message, db, state)
    else:
        await message.answer("Вы ввели не id")



#-----------------------------------------------------------------------
#вывод заметок из БД: id -> name
@fsm_router.message(Command("get_notes")) #add_thoughts
async def command_get_notes_handler(message: Message, db: AsyncPostgres) -> None:
    all_notes = await  db.get_all_notes(message.from_user.id)
    if not all_notes:
        await message.answer("У вас пока нет записей")
        return

    text_message = ""
    for i in range(len( all_notes)):
        note = all_notes[i]
        text_message += f"{i} - {note.get("note_name")}\n"
    text_message = text_message[:-1]

    await message.answer(text_message)

#-----------------------------------------------------------------------------------
@fsm_router.message(Command("get_note"))
async def command_get_note_handler(message: Message,state: FSMContext,  db: AsyncPostgres) -> None:
    # получить заметки
    all_notes = await db.get_all_notes(message.from_user.id)
    if not all_notes:
        await message.answer("У вас пока нет записей")
        return

    all_notes_dict:Dict = {}
    text_message = ""
    for i in range(len( all_notes)):

        note = all_notes[i]
        all_notes_dict[i+1] = note
        text_message += f"{i+1} - {note.get("note_name")}\n"
    text_message = text_message[:-1]


    await message.answer(text_message)
    await message.answer("Напишите id заметки, которую хотите просмотреть")
    await state.set_state(GetNoteIncludings.name)
    await state.update_data(notes =all_notes_dict)


@fsm_router.message(GetNoteIncludings.name)
async def command_get_note_name_stage_handler(message: Message,state: FSMContext,  db: AsyncPostgres) -> None:
    state_data: Dict = await state.get_data()
    all_notes_dict:Dict = state_data.get("notes")
    note_id = message.text

    if  note_id.isdigit() and int(note_id) not in list(all_notes_dict.keys()):
        await message.reply("Вы ввели не тот id")

    elif note_id.isdigit():
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )

        note_id = int(note_id)
        note_db_id = all_notes_dict[note_id].get("note_id")
        # затем по api получаем из контейнера с faiss
        includings = await agent_controller.get_note_thoughts(message.from_user.id, int(note_db_id))
        print("Includings: " ,includings, type(includings))
        if (isinstance(includings, str)):
            await message.answer("Сервис временно не доступен. Попробуйте позже")
        else:
            text_message = ""
            includings = includings['result']
            for category, thoughts in includings:
                    text_message += f"🔥{category}:\n"
                    for i in range(len(thoughts)):
                        thought = thoughts[i]
                        text_message += f"\n{i+1}. {thought["content"]}"
                    text_message += "\n\n"
            await message.reply(text_message)
            await message.bot.send_chat_action(chat_id = message.chat.id, action= ChatAction.TYPING)
            try :
                audio = await agent_controller.get_tts( text_message)
                audio_file = BufferedInputFile(audio, "speech.wav")
                await message.answer_voice(audio_file)
            except Exception as e:
                #logging
                print("EXCEPTION IN SENDING AUDIO ", str(e))

            #await message.answer("Для удаления одной мысли нажмите на кнопку",reply_markup=delete_thoughts_keyboard(includings) )
        await state.clear()

    elif note_id == "/get_notes":
        await state.clear()
        await  command_get_notes_handler(message, db)
    elif note_id == "/delete_note":
        await state.clear()
        await command_delete_note_handler(message, state ,  db)

    elif note_id == "/create_note":
        await state.clear()
        await command_create_note_handler(message, state ,  db)

    elif note_id == "/categories":
        await state.clear()
        await command_categories_handler(message ,state , db)

    elif note_id == "/add_thoughts":
        await state.clear()
        await command_add_note_handler(message, db, state)
    else:
        await message.answer("Вы ввели не id")


@fsm_router.callback_query(CallbackParametrs.filter(F.action == "delete_note_thought"))
async def callback_delete_note_regime(callback: CallbackQuery, callback_data: CallbackParametrs):
       await  callback.message.edit_text("Выберите категорию")
       await callback.message.edit_reply_markup(choose_category_keyboard(callback_data.value))

@fsm_router.callback_query(CallbackParametrs.filter(F.action == "choose_category"))
async def callback_choose_category(callback: CallbackQuery, callback_data: CallbackParametrs):
    await  callback.message.edit_text("Выберите id мысли")
    await callback.message.edit_reply_markup(choose_id_keyboard(callback_data.thoughts))

@fsm_router.callback_query(CallbackParametrs.filter(F.action == "choose_id"))
async def callback_choose_id(callback: CallbackQuery, callback_data: CallbackParametrs):
    print("Callback last ", callback_data)
    thought_id = json.loads(callback_data.thought)["id"]
    compound_id = json.loads(callback_data.thought)["compound_id"]
    try:
        await agent_controller.delete_thought(callback.message.from_user.id, thought_id, compound_id)
        await callback.answer("Все удалено")
    except Exception as e:
        #logging
        print("Problem with deleting callback: ", str(e))
        await callback.answer("Сервис сейчас не доступен, попробуйте позже")



#-------------------------------------------------------------------------------------------
#из бд- выбор заметки для одной заметки
@fsm_router.message(Command('categories'))
async def command_categories_handler(message: Message,state: FSMContext, db: AsyncPostgres) -> None:
    # получаем note_id, note_name  всех записей
    all_notes = await db.get_all_notes(message.from_user.id)
    if not all_notes:
        await message.answer("У вас пока нет записей")
        return
    # если у нас уже много пользователей, в бд id могут быть огромнными, не выводить же их пользователям
    # создаем словарь, где id уже будут равны количеству записей
    all_notes_dict:Dict = defaultdict()
    text_message = ""
    for i in range(len( all_notes)):
        note = all_notes[i]
        all_notes_dict[i+1] = note
        text_message += f"{i+1} - {note.get("note_name")}\n"
    text_message = text_message[:-1]

    await message.answer(text_message)
    await message.answer("Напишите id заметки, у которой вы хотите получить категории")
    await state.set_state(GetNoteCategories.name)
    await state.update_data(notes=all_notes_dict)


@fsm_router.message(GetNoteCategories.name)
async def command_categories_name_stage_handler(message: Message,state: FSMContext, db: AsyncPostgres):
    note_id = message.text
    state_data: Dict = await state.get_data()
    all_notes_dict:Dict = state_data.get("notes")

    if  note_id.isdigit() and int(note_id) not in list(all_notes_dict.keys()):
        await message.reply("Вы ввели не тот id")
        # ждем пока не введет id и не выключаем состояние
    elif note_id.isdigit():
        note_id = int(note_id)
        note_db_id = all_notes_dict[note_id].get("note_id")
        categories = await db.get_categories_by_note_id(note_db_id)

        if len(categories) == 0:
            await message.answer("Заметка пуста, категорий нет")
        else:
            text_message = "<b>⭐️КАТЕГОРИИ:⭐️</b>\n"
            for cat in categories:
                text_message += f"\n{cat.get("category_name")}"

            await message.answer(text_message, parse_mode="html")

        await state.clear()

    elif note_id == "/get-note":
        await state.clear()
        await command_get_note_handler(message, db)
        # чтобы была возможность сразу вызвать другую комманду -> либо оставляем,
        #  либо прописываем так для каждой команды
        # например случайно нажал не ту комманду, и так как тут нет уже долго проходящего сбора данных и операций каких-ибо,
        #  то можно начать другую команду
    elif note_id == "/get_notes":
        await state.clear()
        await  command_get_notes_handler(message, db)

    elif note_id == "/create_note":
        await state.clear()
        await command_create_note_handler(message, state ,  db)

    elif note_id == "/delete_note":
        await state.clear()
        await command_delete_note_handler(message, db, state)
    elif note_id == "/add_thoughts":
        await state.clear()
        await command_add_note_handler(message, db, state)
    else:
        await message.answer("Вы отправили неверный id")



#-----------------------------------------------------------
#


#добавление плана в заметку
@fsm_router.message(Command("add_thoughts")) #add_thoughts
async def command_add_note_handler(message: Message, db: AsyncPostgres, state: FSMContext) -> None:
    all_notes = await db.get_all_notes(message.from_user.id)
    if not all_notes:
        await message.answer("У вас пока нет записей")
        return

    all_notes_dict:Dict = defaultdict()
    text_message = ""
    for i in range(len( all_notes)):
        note = all_notes[i]
        all_notes_dict[i+1] = note
        text_message += f"{i+1} - {note.get("note_name")}\n"
    text_message = text_message[:-1]

    await message.answer(text_message)
    await message.answer("Напишите id заметки, у которой вы хотите получить категории")
    await state.set_state(AddThought.note_id)
    await state.update_data(notes=all_notes_dict)


@fsm_router.message(AddThought.note_id)
async def command_add_note_getting_id(message: Message, db: AsyncPostgres, state: FSMContext) -> None:
    msg = message.text
    state_data: Dict = await state.get_data()
    all_notes:Dict = state_data.get("notes")

    if  msg.isdigit() and int(msg) in list(all_notes.keys()):
        await message.answer("Вышлите голосовое сообщение или аудио для расшифровки")
        await state.update_data(note_id=all_notes[int(msg)].get("note_id"))
        await state.set_state(AddThought.note)

    elif msg == "/get_notes":
        await state.clear()
        await  command_get_notes_handler(message, db)
    elif msg == "/get_note":
        await state.clear()
        await command_get_note_handler(message, state ,  db)

    elif msg == "/categories":
        await state.clear()
        await command_categories_handler(message ,state , db)

    elif msg == "/delete_note":
        await state.clear()
        await command_delete_note_handler(message, db, state)
    else:
        await message.answer("Вы отправили неверный id")




@fsm_router.message(AddThought.note, F.voice)
async def command_add_note_getting_stage_handler(message: Message, db: AsyncPostgres, state: FSMContext, bot: Bot) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action = ChatAction.TYPING)
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    audio_file = io.BytesIO()

    await bot.download_file(file.file_path, destination=audio_file)

    result = await agent_controller.whisper_transcribation(audio_file)
    print("whisper расшифровка :\n" + result)

    #result = "Надо сходить поесть и купить картошку"
    state_data= await state.get_data()
    note_id = state_data.get("note_id")
    try :
         await agent_controller.add_thoughts(message.from_user.id, note_id, result )
         await message.reply("Добавлено")
         await state.clear()
    except Exception as e:
        #logging
        print(str(e))
        await message.answer("Произошла ошибка, попробуйте позже")

    await state.clear()



#обраотка не голосовых сообщений
@fsm_router.message(AddThought.note)
async def command_add_note_getting_stage_handler(message: Message, db: AsyncPostgres, state: FSMContext) -> None:
    msg = message.text
    if msg == "/get_notes":
        await state.clear()
        await  command_get_notes_handler(message, db)
    elif msg == "/get_note":
        await state.clear()
        await command_get_note_handler(message, state ,  db)

    elif msg == "/categories":
        await state.clear()
        await command_categories_handler(message ,state , db)

    elif msg == "/delete_note":
        await state.clear()
        await command_delete_note_handler(message, db, state)
    else:
        await message.answer("Вы не отправили голосовое сообщение")




