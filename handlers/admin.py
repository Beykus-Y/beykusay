from aiogram import types
from services.ai import reset_chat_context
from aiogram.filters import Command
from aiogram.types import User
from services.stats_manager import stats_manager

async def ban_user(message: types.Message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        await message.chat.ban(user.id)
        await message.answer(f"🚨 Пользователь {user.full_name} забанен")

async def warn_user(message: types.Message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        await message.answer(f"⚠️ {user.full_name}, вы получили предупреждение!")

async def show_stats(message: types.Message):
    top_users = stats_manager.get_top_users()
    
    if not top_users:
        await message.answer("📊 Статистика пока недоступна")
        return

    stats_text = ["🏆 Топ активных пользователей:\n"]
    
    for index, (user_id, count) in enumerate(top_users, 1):
        try:
            user = await message.bot.get_chat(user_id)
            name = user.full_name
        except Exception:
            name = f"Пользователь #{user_id}"
            
        stats_text.append(f"{index}. {name}: {count} сообщений")

    await message.answer("\n".join(stats_text))

async def clear_history(message: types.Message):
    user_id = message.from_user.id
    reset_chat_context(user_id)
    await message.answer("🔄 История диалога успешно очищена!")

async def delete_message(message: types.Message):
    if not message.reply_to_message:
        await message.answer("ℹ️ Ответьте (реплай) на сообщение, которое нужно удалить!")
        return

    try:
        await message.reply_to_message.delete()
        await message.delete()
    except Exception as e:
        await message.answer(f"❌ Не удалось удалить сообщение: {str(e)}")