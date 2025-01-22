from aiogram import BaseMiddleware
from aiogram.types import Message, Update
from typing import Callable, Dict, Any, Awaitable
import logging
from services.stats_manager import stats_manager

logger = logging.getLogger(__name__)

class StatsMiddleware(BaseMiddleware):
     async def __call__(self, handler, event, data):
        try:
            if isinstance(event, Message):
                logging.debug(f"Сообщение от {event.from_user.id} → '{event.text}'")

                stats_manager.update_user(event.from_user.id) 
                
        except Exception as e:
            logging.error(f"Ошибка при обработке события: {e}", exc_info=True)
        
        return await handler(event, data)
