from aiogram import BaseMiddleware
from aiogram.types import Message
from controllers.async_db_controller import AsyncPostgres
from typing import Callable, Dict, Awaitable, Any

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db: AsyncPostgres):
        super().__init__()
        self.db = db
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        data['db'] = self.db
        return await handler(event, data)