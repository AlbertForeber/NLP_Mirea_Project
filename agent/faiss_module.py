from typing import Dict, List, Tuple, Optional
from langchain_community.vectorstores import FAISS
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from aiorwlock import RWLock
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import os, shutil, logging, time, asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

@dataclass
class UserIndex():
    user_base: FAISS
    last_active_time: datetime
    personal_lock: asyncio.Lock = asyncio.Lock()

# class UserIndex():
#     user_base: FAISS = Field(description="FAISS пользователя")
#     last_active_time: datetime = Field(description="Последнее время активности (в секундах)")
#     personal_lock: asyncio.Lock = Field(default_factory=asyncio.Lock, description="Персональный блокировщик для действий юзера")

class FaissModule:
    def __init__(self) -> None:
        self.__users_store: Dict[int, UserIndex] = {}
        self.__user_lock: RWLock = RWLock()

        self.__category_store: Optional[FAISS] = None

        BASE_URL = os.getenv("BASE_URL")

        self.__catLock: RWLock = RWLock()

        self.__embeddings = OllamaEmbeddings(
            model="mxbai-embed-large",
            base_url=BASE_URL, #http://77.83.85.58:11435"
            keep_alive=True
        )

        # Инициализация базы категорий
        self.load_or_create_category_store()

        # Запуск цикла очистки неактивных пользователей
        self.__cleaning_task = asyncio.create_task(self.__unload_inactive_user_store())


    async def __get_or_create_user_index(self, user_id: int) -> UserIndex:
        async with self.__user_lock.reader_lock:
            if user_id in self.__users_store.keys():
                self.__users_store[user_id].last_active_time = datetime.now(timezone.utc)

                logging.info(f"FAISS-база для пользователя {user_id} получена из памяти")
                return self.__users_store[user_id]

        try:
            faiss = FAISS.load_local(
                folder_path=f"./data/{user_id}",
                embeddings=self.__embeddings,

                # +-----------------------------------------+
                # | pickle может выполнять вредоносный код. |
                # | этот флаг подтверждает, что мы доверяем |
                # | созданному индексу.                     |
                # +-----------------------------------------+

                allow_dangerous_deserialization=True
            )



            adding_user = UserIndex(user_base=faiss, last_active_time=datetime.now(timezone.utc))
            async with self.__user_lock.writer_lock:
                self.__users_store[user_id] = adding_user

                logging.info(f"FAISS-база для пользователя {user_id} загружена из внутреннего хранилища")
                return self.__users_store[user_id]

        except Exception:
            logger.warning(f"FAISS для пользователя {user_id} не найден. Создание... ")
            return await self.__create_user_store(user_id=user_id)

    async def __create_user_store(self, user_id: int) -> UserIndex:
        faiss = FAISS.from_documents([Document(id=1, page_content="")], embedding=self.__embeddings)
        # Очистка, иначе срабатывает при поиске - ошибка
        faiss.docstore.delete(["1"])


        faiss.save_local(folder_path=f"./data/{user_id}")
        adding_user = UserIndex(user_base=faiss, last_active_time=datetime.now(timezone.utc))

        async with self.__user_lock.writer_lock:
            self.__users_store[user_id] = adding_user

        return self.__users_store[user_id]



    async def __unload_inactive_user_store(self):
        while True:
            # TODO BACK TO MINUTE


            await asyncio.sleep(5)

            to_clean = set()

            async with self.__user_lock.reader_lock:
                for user_id, index in self.__users_store.items():
                    last_active_time = index.last_active_time

                    if datetime.now(timezone.utc) - last_active_time >= timedelta(seconds=15):
                        to_clean.add(user_id)
                        self.__users_store[user_id].user_base.save_local(folder_path=f"./data/{user_id}")


            async with self.__user_lock.writer_lock:
                for user_id in to_clean:
                    if datetime.now(timezone.utc) - self.__users_store[user_id].last_active_time >= timedelta(seconds=15):
                        try:
                            del self.__users_store[user_id]
                            logger.info(f"Пользователь {user_id} очищен")

                        except Exception as e:
                            logger.warning(f"Ошибка при очистке пользователя {user_id}: {e}")


    async def add_new_category(self, suggested_category: str) -> str:
        async with self.__catLock.writer_lock:
            final_category: str = ""
            category_store = self.__category_store

            if category_store:
                result = category_store.similarity_search_with_relevance_scores(suggested_category, k=1, score_threshold=0.8)

                if result:
                    final_category = result[0][0].page_content
                else:
                    category_store.add_texts([suggested_category])
                    final_category = suggested_category

                    logger.info(f"В базу была добавлена категория: '{suggested_category}'")
            else:
                logger.critical("База категорий не была загружена")

        return final_category

    async def remove_thoughts_by_user_id(self, user_id: int):
        async with self.__user_lock.writer_lock:
            if user_id in self.__users_store.keys():
                del self.__users_store[user_id]

        if os.path.exists(f"./data/{user_id}"):
            try:
                shutil.rmtree(f"./data/{user_id}")
                logger.info(f"База пользователя {user_id} удалена")

            except OSError as e:
                logger.error(f"Ошибка при удалении базы пользователя {user_id}")
        else:
            logger.warning(f"Попытка удаления несуществующего пользователя: {user_id}")



    async def add_thoughts(self, user_id: int, thoughts: Dict[str, Dict[str, str]]):
        user_index: UserIndex = await self.__get_or_create_user_index(user_id=user_id)

        documents = [Document(page_content=page_content, metadata=metadata) for page_content, metadata in thoughts.items()]

        async with user_index.personal_lock:
            user_base = user_index.user_base
            user_base.add_documents(documents)

    def load_or_create_category_store(self):
        if self.__category_store != None:
            return

        # не подгружено - лди
        try:
            self.__category_store = FAISS.load_local(
                folder_path = "./data/categories/",
                embeddings = self.__embeddings,
                allow_dangerous_deserialization=True
            )

        except Exception as err:
            self.__category_store = FAISS.from_texts(
                ['Покупки', 'Готовка'],
                self.__embeddings
            )

            self.__category_store.save_local(folder_path=f"./data/categories/")


    async def remove_thought(self, user_id:int, hash_id: str):
        user_index: UserIndex = await self.__get_or_create_user_index(user_id)
        user_store: FAISS = user_index.user_base
        try :
            user_store.delete([hash_id])
            return True
        except Exception as err:
            logger.error(f"Ошибка во время удаления id у {user_id}.\nОшибка: " + str(err))
            return False

    async def remove_thought_by_compound_ids(self, user_id: int, compound_ids: List[int]):
        user_index: UserIndex = await self.__get_or_create_user_index(user_id)
        user_store: FAISS = user_index.user_base
        documents = user_store.docstore.__dict__['_dict']

        to_delete = []

        for doc, val in documents.items():
            compound_id = val.metadata['compound_id']

            if compound_id in compound_ids:
                to_delete.append(doc)

        user_store.delete(to_delete)

    async def get_thoughts_by_compound_id(self, user_id: int, compound_ids: List[int]) -> List[Tuple]:
        user_index: UserIndex = await self.__get_or_create_user_index(user_id)
        user_store: FAISS = user_index.user_base
        documents = user_store.docstore.__dict__['_dict']

        to_return: List[Tuple] = []
        index: Dict[int, int] = {}

        thoughts = []

        for doc, val in documents.items():
                compound_id = val.metadata['compound_id']
                if compound_id in compound_ids:

                    if compound_id in index.keys():
                        to_return[index[compound_id]][1].append({"content": val.page_content, "id": doc, "compound_id": compound_id})
                    else:
                        index[compound_id] = len(to_return)
                        to_return.append((val.metadata["category"], [{"content": val.page_content, "id": doc, "compound_id": compound_id}]))

        return to_return


    async def get_category_for_thought(self, user_id: int, thought: str) -> Optional[str]:
        user_index = await self.__get_or_create_user_index(user_id)
        user_store: FAISS = user_index.user_base


        try:
            similarity = user_store.similarity_search_with_relevance_scores(query = thought,score_threshold =0.75)
        except:
            return None

        if len(similarity) == 0:
            return None
        else:
            return similarity[0][0].metadata["category"]


    def shutdown(self):
        self.__cleaning_task.cancel()
        logger.info("Фоновые задачи FAISS завершены")

