import logging
import g4f
import html
from typing import Dict, List
from config import config
import os
from pathlib import Path
from services.prompt_manager import prompt_manager, AIMode, GeminiModel
from services.context_manager import chat_contexts, reset_chat_context
import google.generativeai as genai
import requests

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

# Настройка Gemini
genai.configure(api_key=config.GEMINI_API_KEY)

# Инициализация базовой модели
default_gemini_model = genai.GenerativeModel(GeminiModel.FLASH_8B.value)

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
        
        settings = prompt_manager.get_settings(chat_id)
        
        if settings.ai_mode == AIMode.PRO:
            try:
                model_type = settings.gemini_model or GeminiModel.FLASH_8B
                gemini_model = genai.GenerativeModel(model_type.value)
                
                chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context])
                response = await gemini_model.generate_content_async(
                    chat_text,
                    generation_config={
                        'temperature': 0.9,
                        'top_p': 0.8,
                    }
                )
                response_text = response.text.strip()
                
                # Sanitize the response for Telegram
                response_text = sanitize_for_telegram(response_text)
                
            except Exception as gemini_error:
                logger.error(f"Ошибка Gemini API: {str(gemini_error)}")
                prompt_manager.set_ai_mode(chat_id, AIMode.DEFAULT)
                return "⚠️ Произошла ошибка с Gemini API. Автоматически переключаюсь на стандартный режим."
        else:
            response = await g4f.ChatCompletion.create_async(
                model=DEFAULT_MODEL,
                messages=context[-MAX_HISTORY_LENGTH:],
                safe_mode=False,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                },
                timeout=config.AI_TIMEOUT,
                temperature=1.0,
                top_p=0.99,
            )
            response_text = response if isinstance(response, str) else "Не удалось обработать ответ нейросети"
            response_text = response_text.strip()

        response_text = html.unescape(response_text)
        response_text = response_text.replace('\u200b', '')
        response_text = response_text.replace('\ufeff', '')
        
        # Make sure response conforms to Telegram's entity restrictions
        response_text = sanitize_for_telegram(response_text)
        
        await add_to_chat_context(chat_id, response_text, "assistant")
        return response_text

    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)
        return "⚠️ Произошла ошибка при генерации ответа. Попробуйте позже."

def sanitize_for_telegram(text: str) -> str:
    """
    Sanitize text to prevent Telegram entity parsing errors.
    This function handles common issues with markdown/HTML formatting.
    """
    # Handle potential unbalanced formatting markers
    markers = ['*', '_', '`', '```', '[', ']', '(', ')', '<', '>']
    
    # Replace special sequences that might confuse Telegram parser
    text = text.replace('\\*', '*')
    text = text.replace('\\_', '_')
    text = text.replace('\\`', '`')
    
    # Balance markdown entities
    for marker in ['*', '_', '`']:
        count = text.count(marker)
        if count % 2 != 0:
            # Find the last occurrence and remove it
            last_index = text.rfind(marker)
            if last_index != -1:
                text = text[:last_index] + text[last_index+1:]
    
    # Check for code blocks
    code_blocks = text.count('```')
    if code_blocks % 2 != 0:
        # Add closing code block
        text += '\n```'
    
    # Check for HTML tags (simplified approach)
    for tag in ['<b>', '<i>', '<code>', '<pre>']:
        closing_tag = '</' + tag[1:]
        if text.count(tag) > text.count(closing_tag):
            text += closing_tag
    
    # Ensure the text doesn't exceed Telegram's message length limit
    if len(text) > MAX_RESPONSE_LENGTH:
        text = text[:MAX_RESPONSE_LENGTH - 3] + '...'
    
    return text