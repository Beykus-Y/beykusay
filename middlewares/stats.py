from aiogram import BaseMiddleware
from aiogram.types import Message, Update
from typing import Callable, Dict, Any, Awaitable
from services.stats_manager import stats_manager

class StatsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        # Обрабатываем только сообщения в группах/супергруппах
        if isinstance(event, Message) and event.chat.type in ["group", "supergroup"]:
            stats_manager.update_user(event.from_user.id)
            print(f"[STATS] Сообщение от {event.from_user.id}")

        return await handler(event, data)