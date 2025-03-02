import logging
import g4f
import html
from typing import Dict, List, Union
from config import config
import os
import re
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
MAX_TELEGRAM_MESSAGE_LENGTH = 2000  # Максимальная длина сообщения в Telegram

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

def split_long_message(message: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> List[str]:
    """
    Разбивает длинное сообщение на части с учетом Markdown-разметки Telegram.
    Сохраняет целостность форматирования (жирный, курсив, код) и разбивает текст
    по абзацам, предложениям или словам, если необходимо.

    Args:
        message (str): Исходный текст с возможной Markdown-разметкой.
        max_length (int): Максимальная длина одной части (по умолчанию 2000 символов).

    Returns:
        List[str]: Список частей сообщения, готовых для отправки в Telegram.
    """
    if len(message) <= max_length:
        return [message]

    parts = []
    current_pos = 0

    # Регулярные выражения для поиска Markdown-форматирования Telegram
    md_patterns = {
        'bold': r'\*(.*?)\*',           # *текст*
        'italic': r'_(.*?)_',           # _текст_
        'code': r'`([^`]+)`',           # `код`
        'pre': r'```(.*?)```',          # ```код```
        'link': r'\[(.*?)\]\((.*?)\)'   # [текст](url)
    }

    # Находим все форматированные блоки
    formatted_blocks = []
    for pattern_type, pattern in md_patterns.items():
        for match in re.finditer(pattern, message, re.DOTALL):
            formatted_blocks.append({
                'start': match.start(),
                'end': match.end(),
            })
    formatted_blocks.sort(key=lambda x: x['start'])

    while current_pos < len(message):
        if len(message) - current_pos <= max_length:
            parts.append(message[current_pos:])
            break

        # Предполагаемая точка среза
        cut_pos = current_pos + max_length

        # Проверяем, не пересекаем ли форматированный блок
        safe_cut_pos = cut_pos
        for block in formatted_blocks:
            if current_pos <= block['start'] < cut_pos < block['end']:
                # Разрез внутри блока — сдвигаем точку среза до начала блока
                safe_cut_pos = min(safe_cut_pos, block['start'])
                break

        # Если форматирование не нарушено, ищем естественную точку разрыва
        if safe_cut_pos == cut_pos:
            # Ищем перенос строки
            newline_pos = message.rfind('\n', current_pos, cut_pos)
            if newline_pos > current_pos + max_length // 2:
                safe_cut_pos = newline_pos + 1
            else:
                # Ищем точку конца предложения
                sentence_pos = message.rfind('. ', current_pos, cut_pos)
                if sentence_pos > current_pos + max_length // 2:
                    safe_cut_pos = sentence_pos + 2
                else:
                    # Ищем последний пробел
                    space_pos = message.rfind(' ', current_pos, cut_pos)
                    if space_pos > current_pos + max_length // 2:
                        safe_cut_pos = space_pos + 1

        # Если безопасная точка не найдена, используем максимальную длину
        if safe_cut_pos == cut_pos:
            safe_cut_pos = cut_pos

        # Добавляем часть текста
        parts.append(message[current_pos:safe_cut_pos])
        current_pos = safe_cut_pos

    return parts

async def get_ai_response(chat_id: int, text: str) -> Union[str, List[str]]:
    try:
        await add_to_chat_context(chat_id, text)
        context = chat_contexts.get(chat_id, [])
        
        settings = prompt_manager.get_settings(chat_id)
        
        try:
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
            
            # Сохраняем полный ответ в контексте
            await add_to_chat_context(chat_id, response_text, "assistant")
            
            # Проверка типа и преобразование для безопасности
            if not isinstance(response_text, str):
                response_text = str(response_text)
            
            # Разбиваем ответ на части для отправки в Telegram
            message_parts = split_long_message(response_text, MAX_TELEGRAM_MESSAGE_LENGTH)
            
            # Проверяем, что все элементы списка - строки
            message_parts = [str(part) for part in message_parts]
            
            # Если сообщение всего одно, возвращаем строку, иначе список строк
            if len(message_parts) == 1:
                return message_parts[0]
            else:
                return message_parts
                
        except Exception as inner_e:
            logger.error(f"Внутренняя ошибка генерации: {str(inner_e)}", exc_info=True)
            return "⚠️ Произошла ошибка при обработке ответа. Попробуйте еще раз."

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
    
    # Возвращаем текст без ограничения длины, так как разбивка будет выполнена в split_long_message
    return text