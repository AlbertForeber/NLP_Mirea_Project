from fastapi import FastAPI, HTTPException, status
from faiss_module import FaissModule
from llm_module import LLMModule
from postgres_module import PostgresModule
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel
import logging, asyncio, sys


logger = logging.getLogger()

class Thoughts(BaseModel):
    result: List[Tuple]

class ErrorResponse(BaseModel):
    error: str # Читаемое описание

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Инициализация необходимых модулей с обработкой ошибок
    """

    app.state.faiss = None
    app.state.llm = None
    app.state.db = None

    try:
        app.state.faiss = FaissModule()
        logger.info("FAISS инициализирован")

        app.state.llm = LLMModule()
        logger.info("LLM инициализирован")


        app.state.db = PostgresModule()
        try:
            await asyncio.wait_for(app.state.db.connect(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Время подключения к БД истекло")
            # Запуск прерывается
            raise
    except Exception as e:
        logger.critical(
            f"Не удалось инициализировать приложение: {str(e)}",
            exc_info=True # Вывод traceback
        )

        sys.exit(1)

    yield

    logger.info("Завершение работы приложения...")
    try:
        db: PostgresModule = app.state.db
        faiss: FaissModule = app.state.faiss

        try:
            await asyncio.wait_for(db.disconnect(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Время отключения от БД истекло")
            raise

        faiss.shutdown()
    except Exception as e:
        logger.error(
            f"Работа завершена с ошибкой: {str(e)}",
            exc_info=True # Вывод traceback
        )

        sys.exit(1)


app = FastAPI(
    title="Agent Module",
    description="Responsible for work with FAISS and LLM",
    version="1.0.0",
    lifespan=lifespan
)

# Usage example /add_thoughts/?user_id=1&note_id=2
@app.post("/add-thoughts/")
async def add_thoughts(user_id: int, note_id: int, speech: str):
    faiss: FaissModule = app.state.faiss
    llm: LLMModule = app.state.llm
    db: PostgresModule = app.state.db

    try:
        # Splitting into thoughts
        try:
            thoughts: List[str] | None = await asyncio.wait_for(llm.split_into_thoughts(text=speech), 180)
        except asyncio.TimeoutError as e:
            logger.error("Превышено время ожидания ответа LLM")

            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ErrorResponse(error="Превышено время ожидания ответа LLM").model_dump()
            )

        print("Список извлеченных мыслей")
        print(thoughts)

        if thoughts:
            thought_with_metadata: Dict[str, Dict[str, str]] = {}
            generate_categories_for: List[str] = []

            for thought in thoughts:
                try:
                    res = await asyncio.wait_for(faiss.get_category_for_thought(user_id, thought), 30)
                except asyncio.TimeoutError:
                    logger.error("Превышено время ожидания ответа FAISS")

                    raise HTTPException(
                        status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=ErrorResponse(error="Превышено время ожидания ответа FAISS").model_dump()
                    )

                thought_with_metadata[thought] = {}

                if not res:
                    thought_with_metadata[thought]["category"] = ""
                    generate_categories_for.append(thought)
                else:
                    thought_with_metadata[thought]["category"] = res



            for thought in generate_categories_for:
                try:
                    res = await asyncio.wait_for(llm.generate_new_category(thought), 180)
                except asyncio.TimeoutError:
                    logger.error("Превышено время ожидания ответа LLM")

                    raise HTTPException(
                        status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=ErrorResponse(error="Превышено время ожидания ответа LLM").model_dump()
                    )

                thought_with_metadata[thought]["category"] = await faiss.add_new_category(res)


            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    for thought, metadata in thought_with_metadata.items():
                        metadata["compound_id"] = await db.get_compound_id(note_id, metadata["category"], conn)

                    try:
                        await asyncio.wait_for(faiss.add_thoughts(user_id, thought_with_metadata), 30)
                    except asyncio.TimeoutError:
                        logger.error("Превышено время ожидания ответа FAISS")

                        raise HTTPException(
                            status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=ErrorResponse(error="Превышено время ожидания ответа FAISS").model_dump()
                        )

            print(thought_with_metadata)

            return {
                "status": "success",
                "thoughts_added": len(thought_with_metadata)
            }

    except Exception as e:
        logger.error("Ошибка добавления мыслей в память", exc_info=True)
        raise HTTPException(
                            status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=ErrorResponse(error="Ошибка добавления мыслей в память").model_dump()
                        )






@app.get("/get-note-thoughts/", response_model=Thoughts)
async def get_note_thoughts(user_id: int, note_id: int):
    faiss: FaissModule = app.state.faiss
    db: PostgresModule = app.state.db

    note_compounds = await db.get_note_compounds(note_id)

    try:
        result = await asyncio.wait_for(faiss.get_thoughts_by_compound_id(user_id, note_compounds), 30)
    except asyncio.TimeoutError:
        logger.error("Превышено время ожидания ответа FAISS")


        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(error="Превышено время ожидания FAISS").model_dump()
            )
    except Exception as e:
        logger.error("Ошибка при возврате мыслей", exc_info=True)

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="Ошибка при возврате мыслей").model_dump()
            )



    return Thoughts(result=result)


@app.delete("/delete-thought/")
async def delete_thought(user_id: int, document_id: str, compound_id: int):
    faiss: FaissModule = app.state.faiss
    db: PostgresModule = app.state.db

    try:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                await db.thought_deleted(compound_id, conn)

                try:
                    await asyncio.wait_for(faiss.remove_thought(user_id, document_id), 30)
                except asyncio.TimeoutError:
                    logger.error("Превышено время ожидания ответа FAISS")

                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=ErrorResponse(error="Превышено время ожидания FAISS").model_dump()
                    )

    except Exception as _:
        logger.error("Ошибка удаления мысли", exc_info=True)

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="Ошибка удаления мысли").model_dump()
            )


    return {"status" : "success"}


@app.delete("/delete-user/")
async def delete_user(user_id: int):
    faiss: FaissModule = app.state.faiss
    db: PostgresModule = app.state.db

    try:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                await db.delete_user(user_id, conn)

                try:
                    await asyncio.wait_for(faiss.remove_thoughts_by_user_id(user_id), 30)
                except asyncio.TimeoutError:
                    logger.error("Превышено время ожидания ответа FAISS")

                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=ErrorResponse(error="Превышено время ожидания FAISS").model_dump()
                    )

    except Exception as _:
        logger.error("Ошибка удаления пользователя", exc_info=True)

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="Ошибка удаления пользователя").model_dump()
            )


    return {"status" : "success"}



@app.delete("/delete-note/")
async def delete_note(user_id, note_id):
    faiss: FaissModule = app.state.faiss
    db: PostgresModule = app.state.db

    note_compounds = await db.get_note_compounds(note_id)

    try:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                await db.delete_note(note_id, conn)

                try:
                    await asyncio.wait_for(faiss.remove_thought_by_compound_ids(user_id, note_compounds), 30)
                except asyncio.TimeoutError:
                    logger.error("Превышено время ожидания ответа FAISS")

                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=ErrorResponse(error="Превышено время ожидания FAISS").model_dump()
                    )

    except Exception as _:
        logger.error("Ошибка удаления заметки", exc_info=True)

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="Ошибка удаления заметки").model_dump()
            )

    return {"status" : "success"}
