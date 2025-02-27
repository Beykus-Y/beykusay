from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from typing import Callable, Dict, Any, Awaitable
import time
import asyncio

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit=5):
        self.limit = limit
        self.user_messages = {}
        self.warning_sent = {}  # Словарь для отслеживания предупреждений

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event.event, Message):
            return await handler(event, data)

        user_id = event.event.from_user.id
        current_time = time.time()
        username = event.event.from_user.username or event.event.from_user.first_name
        
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        
        # Очищаем старые сообщения
        self.user_messages[user_id] = [
            t for t in self.user_messages[user_id] 
            if current_time - t < 60
        ]
        
        # Очищаем старые предупреждения
        if user_id in self.warning_sent and current_time - self.warning_sent[user_id] > 60:
            del self.warning_sent[user_id]
        
        if len(self.user_messages[user_id]) >= self.limit:
            # Удаляем спам-сообщение
            await event.event.delete()
            
            # Отправляем предупреждение только если ещё не отправляли
            if user_id not in self.warning_sent:
                warning_text = f"@{username}, слишком много сообщений! Подождите минуту."
                sent_message = await event.event.answer(
                    warning_text,
                    reply_to_message_id=event.event.message_id
                )
                self.warning_sent[user_id] = current_time
                
                # Удаляем предупреждение через 5 секунд
                await asyncio.sleep(5)
                await sent_message.delete()
            
            return
        
        self.user_messages[user_id].append(current_time)
        return await handler(event, data)