import logging
import g4f
import html
from typing import Dict, List
from config import config
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Настройки по умолчанию
DEFAULT_MODEL = "gpt-4"
MAX_HISTORY_LENGTH = config.MAX_HISTORY_LENGTH
MAX_RESPONSE_LENGTH = config.MAX_MESSAGE_LENGTH

def load_system_prompt() -> str:
    prompt_path = Path("system_prompt.txt")
    
   
    default_prompt = """Ты - ассистент в групповом чате, отвечай только на русском"""
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Ошибка загрузки промпта: {e}. Используется дефолтная версия")
        return default_prompt

SYSTEM_PROMPT = load_system_prompt()

from g4f.Provider import (
    Liaobots,
    DDG,
    You,
    AIUncensored,
    Blackbox,
    Chatgpt4o,
    GPTalk
)

# Глобальное хранилище контекста диалогов
chat_contexts: Dict[int, List[dict]] = {}

async def add_to_chat_context(chat_id: int, text: str, role: str = "user"):
    try:
        # Инициализация контекста с системным промптом
        if chat_id not in chat_contexts:
            chat_contexts[chat_id] = [{
                "role": "system",
                "content": SYSTEM_PROMPT
            }]
        
        # Добавляем новое сообщение
        chat_contexts[chat_id].append({"role": role, "content": text.strip()})
        
        # Обрезаем историю, сохраняя системный промпт
        max_messages = MAX_HISTORY_LENGTH + 1  # +1 слот для системного сообщения
        chat_contexts[chat_id] = (
            [chat_contexts[chat_id][0]] +  # Всегда сохраняем системный промпт
            chat_contexts[chat_id][1:][-max_messages+1:]  # Обрезаем остальные сообщения
        )[:max_messages]

    except Exception as e:
        logger.error(f"Ошибка добавления в контекст: {str(e)}")
        # Восстанавливаем системный промпт при критической ошибке
        if chat_id in chat_contexts and len(chat_contexts[chat_id]) == 0:
            chat_contexts[chat_id] = [{
                "role": "system",
                "content": SYSTEM_PROMPT
            }]

def split_long_message(message: str) -> List[str]:
    """Разделение длинных сообщений на части"""
    return [message[i:i+MAX_RESPONSE_LENGTH] for i in range(0, len(message), MAX_RESPONSE_LENGTH)]

async def get_ai_response(chat_id: int, text: str) -> str:
    """Генерация ответа через автоматический выбор провайдера"""
    try:
        await add_to_chat_context(chat_id, text)
        context = chat_contexts.get(chat_id, [])
        
        # Генерация ответа с кастомными заголовками
        response = await g4f.ChatCompletion.create_async(
            #model=DEFAULT_MODEL,
            model = "hermes3-70b",
            messages=context,
            safe_mode=False,
            provider=AIUncensored,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            },
            timeout=config.AI_TIMEOUT,
            temperature=1.0,  # Исправлено на допустимое значение
            top_p=0.99,
            
        )

        if isinstance(response, str):
            response = html.unescape(response)
            await add_to_chat_context(chat_id, response, "assistant")
            return response
            
        return "Не удалось обработать ответ нейросети"

    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)
        return "⚠️ Все провайдеры недоступны. Попробуйте позже."

def reset_chat_context(chat_id: int):
    """Сброс контекста диалога"""
    try:
        if chat_id in chat_contexts:
            del chat_contexts[chat_id]
            logger.info(f"Контекст чата {chat_id} сброшен")
    except Exception as e:
        logger.error(f"Ошибка сброса: {str(e)}")