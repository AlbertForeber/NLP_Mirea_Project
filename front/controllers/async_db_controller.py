import asyncpg
from typing import Optional
import os
class AsyncPostgres:
    def __init__(self):
        self.dns = os.getenv('dns')
        #self.dns = "postgresql://postgres:postgres@localhost:5432/books"
        #postgresql://username:password@hostname:port/database_name
        #│          │         │         │        │       │
        #протокол   логин     пароль    хост     порт   имя БД
        self.pool:  Optional[asyncpg.Pool] = None

    async def connect(self):
        """Функция подключения - создания пула"""
        self.pool = await asyncpg.create_pool(dsn=self.dns, min_size=5, max_size=20)

    async def disconnect(self):
        """Функция отключения - закртыие пула"""
        if self.pool:
            await self.pool.close()


    async def add_new_note(self,user_id,  note_name):
        async with self.pool.acquire() as conn:
            return await conn.execute(f"""
                                      INSERT INTO notes (note_name, user_id) VALUES ('{note_name}', '{user_id}')
                                      """)

    async def get_all_notes(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetch(f"SELECT note_id, note_name FROM notes WHERE user_id = '{user_id}'")

    async def get_categories_by_note_id(self, note_id):
        async with self.pool.acquire() as conn:
            # поенмятьна note_category
            return await conn.fetch(f"""SELECT category_name FROM categories AS c
                                        RIGHT JOIN note_category AS nm ON nm.category_id = c.category_id
                                        WHERE nm.note_id = {note_id}""")

    async def add_user(self, user_id, user_name):
        async with self.pool.acquire() as conn:
            return await conn.execute(f"INSERT INTO users(telegram_id, user_name ) VALUES ('{user_id}', '{user_name}') ON CONFLICT DO NOTHING;")

    # async def delete_note(self, note_id: int):
    #     async with self.pool.acquire() as conn:
    #         return await conn.execute(f"DELETE FROM notes WHERE note_id = {note_id}")