import logging
import g4f
import html
from typing import Dict, List
from config import config
import os
from pathlib import Path
from services.prompt_manager import prompt_manager
from services.context_manager import chat_contexts, reset_chat_context

logger = logging.getLogger(__name__)

# Настройки по умолчанию
DEFAULT_MODEL = "gpt-4"
MAX_HISTORY_LENGTH = config.MAX_HISTORY_LENGTH
MAX_RESPONSE_LENGTH = config.MAX_MESSAGE_LENGTH

from g4f.Provider import (
    Liaobots,
    DDG,
    You,
    AIUncensored,
    Blackbox,
    Chatgpt4o,
    GPTalk
)


async def add_to_chat_context(chat_id: int, text: str, role: str = "user"):
    try:
        if chat_id not in chat_contexts:
            combined_prompt = prompt_manager.get_combined_prompt(chat_id)
            chat_contexts[chat_id] = [{
                "role": "system", 
                "content": combined_prompt
            }]
        
        chat_contexts[chat_id].append({"role": role, "content": text.strip()})
        
        chat_contexts[chat_id] = (
            [chat_contexts[chat_id][0]] + 
            chat_contexts[chat_id][1:][-MAX_HISTORY_LENGTH+1:]
        )[:MAX_HISTORY_LENGTH+1]

    except Exception as e:
        logger.error(f"Context error: {str(e)}")
        if chat_id in chat_contexts and len(chat_contexts[chat_id]) == 0:
            combined_prompt = prompt_manager.get_combined_prompt(chat_id)
            chat_contexts[chat_id] = [{"role": "system", "content": combined_prompt}]

def split_long_message(message: str) -> List[str]:
    return [message[i:i+MAX_RESPONSE_LENGTH] for i in range(0, len(message), MAX_RESPONSE_LENGTH)]

async def get_ai_response(chat_id: int, text: str) -> str:
    try:
        await add_to_chat_context(chat_id, text)
        context = chat_contexts.get(chat_id, [])
        
        response = await g4f.ChatCompletion.create_async(
            #model=DEFAULT_MODEL,
            model = "hermes3-70b",
            messages=context[-MAX_HISTORY_LENGTH:],
            safe_mode=False,
            provider=AIUncensored,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            },
            timeout=config.AI_TIMEOUT,
            temperature=1.0, 
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
