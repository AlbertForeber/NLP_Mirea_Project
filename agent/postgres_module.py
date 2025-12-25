
import os
import logging
import asyncpg, asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class PostgresModule:
    def __init__(self) -> None:
        self.pool = None

    async def connect(self):
        db_dsn = os.getenv("DB_DSN", "")

        self.pool = await asyncpg.create_pool(
            dsn=db_dsn,
            min_size=5,
            max_size=10
        )

        logger.info("Успешное подключение к БД")

    async def disconnect(self):
        await self.pool.close()

        logger.info("Успешное отключение от БД")

    async def delete_user(self, user_id, conn):
        await conn.execute(f"DELETE FROM users WHERE user_id={user_id}")

    async def delete_note(self, note_id, conn):
        await conn.execute(f"DELETE FROM notes WHERE note_id={note_id}")

    async def get_or_create_compound_id(self, note_id: int, category_id: int, conn: asyncpg.pool.PoolConnectionProxy):
        result = await conn.fetchval(f"""
            WITH attempt AS (
                INSERT INTO note_category (note_id, category_id, thought_count)
                VALUES ({note_id}, {category_id}, 0) ON CONFLICT (note_id, category_id) DO NOTHING
                RETURNING compound_id
            )

            SELECT compound_id FROM attempt
            UNION ALL
            SELECT compound_id FROM note_category
            WHERE note_id = {note_id} AND category_id = {category_id}
            LIMIT 1
        """)
        await conn.execute(f"""
            UPDATE note_category
            SET thought_count = thought_count + 1
            WHERE compound_id={result}
        """)

        return result

    async def get_or_create_category_id(self, category_name, conn: asyncpg.pool.PoolConnectionProxy) :
        category_id = await conn.fetchval(f"""
                                WITH attempt AS (
                                            INSERT INTO categories (category_name)
                                            VALUES ('{category_name}')
                                            ON CONFLICT (category_name) DO NOTHING
                                            RETURNING category_id
                                                                )
                                SELECT category_id from attempt
                                UNION ALL
                                SELECT category_id FROM categories
                                WHERE category_name = '{category_name}'
                                LIMIT 1;

                                """)
        return category_id

    async def get_compound_id(self, note_id, category_name, conn):
        cat_id = await self.get_or_create_category_id(category_name, conn)
        compound_id = await self.get_or_create_compound_id(note_id, cat_id, conn)
        return compound_id

    async def get_note_compounds(self, note_id):
        async with self.pool.acquire() as conn:
            result = await conn.fetch(f"SELECT compound_id FROM note_category WHERE note_id={note_id}")
            return [record['compound_id'] for record in result]

    async def thought_deleted(self, compound_id, conn):
        await conn.execute(f"""
                UPDATE note_category
                SET thought_count = thought_count - 1
                WHERE compound_id={compound_id}
            """)


async def main():
    module = PostgresModule()
    await module.connect()
    print(await module.get_note_compounds(1))

if __name__ == "__main__":
    asyncio.run(main())