from aiogram import types, Bot
from config import config
from services import ai, moderation
import logging

async def handle_message(message: types.Message, bot: Bot):
    # Проверка модерации
    if moderation.contains_bad_words(message.text):
        try:
            await message.delete()
            await message.answer("🚫 Сообщение удалено за нарушение правил!")
        except Exception as e:
            logging.error(f"Ошибка удаления: {e}")
        return

    # Получаем информацию о боте
    bot_info = await bot.get_me()
    bot_username = bot_info.username.lower()
    bot_id = bot_info.id

    # Проверяем условия ответа
    should_respond = False

    # 1. Проверка реплая на сообщение бота
    if message.reply_to_message and message.reply_to_message.from_user.id == bot_id:
        should_respond = True

    # 2. Проверка упоминания @username бота
    if f"@{bot_username}" in message.text.lower():
        should_respond = True

    # 3. Проверка упоминания через ID (для приватных ботов)
    if str(bot_id) in message.text:
        should_respond = True

    if not should_respond:
        return

    # Генерация ответа
    try:
        response = await ai.get_ai_response(message.from_user.id, message.text)
        for chunk in ai.split_long_message(response):
            await message.reply(chunk[:config.MAX_MESSAGE_LENGTH], parse_mode="Markdown")
            
    except Exception as e:
        logging.error(f"Ошибка генерации: {str(e)}")
        await message.reply("⚠️ Произошла ошибка при обработке запроса")