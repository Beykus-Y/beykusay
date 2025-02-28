from aiogram import types, Bot
from aiogram.enums import ContentType
from config import config
from services import ai, moderation
from services.stats_manager import stats_manager
import logging
from aiogram.exceptions import TelegramNetworkError
import asyncio

logger = logging.getLogger(__name__)

import re
import logging
import asyncio
from typing import List
from aiogram import Bot, types
from aiogram.types import ContentType
from aiogram.exceptions import TelegramNetworkError

async def handle_message(message: types.Message, bot: Bot):
    # Проверка и сохранение в статистику
    if (
        message.chat.type in {"group", "supergroup"} 
        and message.content_type == ContentType.TEXT
        and not message.from_user.is_bot
    ):
        try:
            stats_manager.update_user(message.chat.id, message.from_user.id)
            logging.info(f"Статистика обновлена для {message.from_user.id}")
        except Exception as e:
            logging.error(f"Ошибка статистики: {e}")
    
    # Защита от отсутствия текста
    if not message.text:
        return
    
    # Проверка на плохие слова
    if moderation.contains_bad_words(message.text):
        try:
            await message.delete()
            await message.answer("🚫 Сообщение удалено за нарушение правил!")
        except Exception as e:
            logging.error(f"Ошибка удаления: {e}")
        return
        
    # Добавляем ВСЕ сообщения в контекст чата
    if message.chat.type in {"group", "supergroup"} and not message.from_user.is_bot:
        try:
            await ai.add_to_chat_context(
                chat_id=message.chat.id,
                text=message.text,
                role="user"
            )
        except Exception as e:
            logging.error(f"Ошибка сохранения контекста: {e}")
            
    # Получаем информацию о боте с обработкой таймаутов
    max_retries = 3
    bot_info = None
    for attempt in range(max_retries):
        try:
            bot_info = await bot.get_me()
            break
        except TelegramNetworkError:
            if attempt == max_retries - 1:
                await message.answer("⚠️ Сервер Telegram недоступен. Попробуйте позже.")
                return
            await asyncio.sleep(2)
    
    # Проверка условий ответа
    bot_username = bot_info.username.lower()
    bot_id = bot_info.id
    should_respond = (
        message.reply_to_message 
        and message.reply_to_message.from_user.id == bot_id
    ) or any([
        f"@{bot_username}" in message.text.lower(),
        str(bot_id) in message.text
    ])
    
    if not should_respond:
        return
        
    # Генерация ответа
    try:
        # Показываем, что бот печатает
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Получаем ответ от AI
        response = await ai.get_ai_response(chat_id=message.chat.id, text=message.text)
        
        # Обрабатываем ответ в зависимости от типа
        if isinstance(response, list):
            parts = []
            # Объединяем части обратно, чтобы правильно обработать форматирование
            full_response = "".join(response)
            # И разбиваем с учетом форматирования
            parts = split_markdown_safe(full_response, max_length=2000)
        else:
            parts = split_markdown_safe(response, max_length=2000)
        
        # Отправляем каждую часть
        for part in parts:
            if not part:  # Пропускаем пустые части
                continue
                
            try:
                await message.reply(text=part, parse_mode="Markdown")
            except Exception as part_error:
                logging.error(f"Ошибка отправки части сообщения: {str(part_error)}")
                # Пробуем отправить без форматирования
                try:
                    await message.reply(text=part, parse_mode=None)
                except Exception:
                    # Если и это не помогло, пробуем очистить разметку
                    clean_part = remove_markdown(part)
                    await message.reply(text=clean_part[:2000])
                    
    except Exception as e:
        logging.error(f"Ошибка генерации: {str(e)}", exc_info=True)
        try:
            await message.reply("⚠️ Произошла ошибка при обработке запроса")
        except Exception as reply_error:
            logging.error(f"Не удалось отправить сообщение об ошибке: {str(reply_error)}")

def remove_markdown(text: str) -> str:
    """Удаляет разметку Markdown из текста"""
    # Удаляем символы форматирования
    patterns = [
        r'\*\*(.*?)\*\*',  # Bold
        r'\*(.*?)\*',      # Italic
        r'__(.*?)__',      # Underline
        r'_([^_]+)_',      # Italic
        r'`(.*?)`',        # Code
        r'```(.*?)```',    # Code block
        r'\[(.*?)\]\((.*?)\)'  # Links
    ]
    
    result = text
    for pattern in patterns:
        result = re.sub(pattern, r'\1', result)
    
    return result

def split_markdown_safe(text: str, max_length: int = 2000) -> List[str]:
    """
    Разбивает сообщение на части с сохранением корректности Markdown-разметки.
    
    Args:
        text: Исходный текст с Markdown-разметкой
        max_length: Максимальная длина каждого сообщения
        
    Returns:
        Список сообщений, готовых для отправки
    """
    if len(text) <= max_length:
        return [text]
    
    # Регулярное выражение для поиска Markdown-форматирования
    md_patterns = {
        'bold': r'\*\*(.*?)\*\*',
        'italic': r'\*(.*?)\*',
        'underline': r'__(.*?)__',
        'italic_alt': r'_([^_]+)_',
        'code': r'`(.*?)`',
        'code_block': r'```(.*?)```',
        'link': r'\[(.*?)\]\((.*?)\)'
    }
    
    # Находим все форматированные блоки в тексте
    formatted_blocks = []
    for pattern_type, pattern in md_patterns.items():
        for match in re.finditer(pattern, text, re.DOTALL):
            formatted_blocks.append({
                'type': pattern_type,
                'start': match.start(),
                'end': match.end(),
                'text': match.group(0)
            })
    
    # Сортируем блоки по начальной позиции
    formatted_blocks.sort(key=lambda x: x['start'])
    
    parts = []
    current_pos = 0
    
    while current_pos < len(text):
        # Если оставшаяся часть текста меньше max_length, добавляем ее целиком
        if len(text) - current_pos <= max_length:
            parts.append(text[current_pos:])
            break
        
        # Ищем хорошее место для разделения
        cut_pos = current_pos + max_length
        
        # Проверяем, не разрезаем ли мы форматированный блок
        safe_cut_pos = cut_pos
        for block in formatted_blocks:
            if current_pos < block['start'] < cut_pos < block['end']:
                # Мы в середине форматированного блока, ищем позицию до начала блока
                safe_cut_pos = min(safe_cut_pos, block['start'])
            elif block['start'] <= current_pos < block['end'] <= cut_pos:
                # Блок начинается в текущей части и заканчивается в ней же
                pass
            elif current_pos <= block['start'] < block['end'] <= cut_pos:
                # Блок полностью внутри текущей части
                pass
            elif block['start'] <= current_pos < cut_pos < block['end']:
                # Блок начинается до или в текущей части и продолжается после нее
                # Ищем позицию после конца блока
                safe_cut_pos = min(safe_cut_pos, current_pos + max_length // 2)
        
        # Если не нашли безопасную позицию из-за блока, ищем конец последнего предложения или абзаца
        if safe_cut_pos < current_pos + max_length // 2:
            # Ищем последний перенос строки
            newline_pos = text.rfind('\n', current_pos, cut_pos)
            if newline_pos > current_pos + max_length // 3:
                safe_cut_pos = newline_pos + 1
            else:
                # Ищем последнюю точку с пробелом
                sentence_pos = text.rfind('. ', current_pos, cut_pos)
                if sentence_pos > current_pos + max_length // 3:
                    safe_cut_pos = sentence_pos + 2
                else:
                    # Ищем последний пробел
                    space_pos = text.rfind(' ', current_pos, cut_pos)
                    if space_pos > current_pos + max_length // 3:
                        safe_cut_pos = space_pos + 1
                    else:
                        # Если ничего не нашли, просто разрезаем по максимальной длине
                        safe_cut_pos = cut_pos
        
        # Добавляем текущую часть
        parts.append(text[current_pos:safe_cut_pos])
        current_pos = safe_cut_pos
    
    # Проверяем целостность Markdown в каждой части и исправляем при необходимости
    balanced_parts = []
    md_markers = ['*', '**', '_', '__', '`', '```']
    
    for part in parts:
        # Проверяем балансировку маркеров форматирования
        balanced_part = part
        for marker in md_markers:
            count = balanced_part.count(marker)
            if count % 2 != 0:
                # Находим последнее вхождение и удаляем его, если оно на конце
                last_idx = balanced_part.rfind(marker)
                if last_idx > len(balanced_part) - len(marker) - 10:  # Если маркер близко к концу
                    balanced_part = balanced_part[:last_idx] + balanced_part[last_idx+len(marker):]
        
        balanced_parts.append(balanced_part)
    
    return balanced_parts