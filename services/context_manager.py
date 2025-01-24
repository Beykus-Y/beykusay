# services/context_manager.py
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# Глобальное хранилище контекста
chat_contexts: Dict[int, list] = {}

def reset_chat_context(chat_id: int):
    try:
        if chat_id in chat_contexts:
            del chat_contexts[chat_id]
            logger.info(f"Context reset for chat {chat_id}")
    except Exception as e:
        logger.error(f"Context reset error: {str(e)}")