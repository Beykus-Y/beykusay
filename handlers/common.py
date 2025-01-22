from aiogram import types, Bot
from aiogram.enums import ContentType
from config import config
from services import ai, moderation
from services.stats_manager import stats_manager
import logging

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
    
    # Проверка на плохие слова
    if moderation.contains_bad_words(message.text):
        try:
            await message.delete()
            await message.answer("🚫 Сообщение удалено за нарушение правил!")
        except Exception as e:
            logging.error(f"Ошибка удаления: {e}")
        return

    # Добавляем ВСЕ сообщения в контекст чата (даже если бот не ответит)
    if message.chat.type in {"group", "supergroup"} and not message.from_user.is_bot:
        try:
            # Сохраняем сообщение в историю чата
            await ai.add_to_chat_context(
                chat_id=message.chat.id,
                text=message.text,
                role="user"
            )
        except Exception as e:
            logging.error(f"Ошибка сохранения контекста: {e}")

    # Проверка условий ответа (без изменений)
    bot_info = await bot.get_me()
    bot_username = bot_info.username.lower()
    bot_id = bot_info.id

    should_respond = False
    if message.reply_to_message and message.reply_to_message.from_user.id == bot_id:
        should_respond = True
    if f"@{bot_username}" in message.text.lower():
        should_respond = True
    if str(bot_id) in message.text:
        should_respond = True

    if not should_respond:
        return

    # Генерация ответа с использованием общего контекста чата
    try:
        response = await ai.get_ai_response(chat_id=message.chat.id, text=message.text)
        for chunk in ai.split_long_message(response):
            await message.reply(chunk[:config.MAX_MESSAGE_LENGTH], parse_mode="Markdown")
            
    except Exception as e:
        logging.error(f"Ошибка генерации: {str(e)}")
        await message.reply("⚠️ Произошла ошибка при обработке запроса")