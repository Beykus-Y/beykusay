from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from typing import Callable, Dict, Any, Awaitable

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit=5):
        self.limit = limit
        self.user_messages = {}

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        current_time = event.date.timestamp()
        
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        
        self.user_messages[user_id] = [
            t for t in self.user_messages[user_id] 
            if current_time - t < 60
        ]
        
        if len(self.user_messages[user_id]) >= self.limit:
            await event.answer("Слишком много сообщений! Подождите минуту.")
            return
        
        self.user_messages[user_id].append(current_time)
        return await handler(event, data)