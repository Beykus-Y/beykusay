from aiogram import types
from services.ai import reset_chat_context
from services.warn_manager import warn_manager
from aiogram.filters import Command
from aiogram.types import User
from services.stats_manager import stats_manager

async def ban_user(message: types.Message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        await message.chat.ban(user.id)
        await message.answer(f"🚨 Пользователь {user.full_name} забанен")

async def warn_user(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя!")
        return

    user = message.reply_to_message.from_user
    warn_count = warn_manager.add_warn(user.id)
    
    await message.answer(
        f"⚠️ {user.full_name} получил предупреждение! "
        f"Теперь у него {warn_count}/5 варнов."
    )

    if warn_count >= 5:
        await message.chat.ban(user.id)
        await message.answer(f"🚨 {user.full_name} забанен за 5 предупреждений!")
        warn_manager.remove_warn(user.id, 5)  # Сброс варнов

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

async def unwarn_user(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя!")
        return

    try:
        count = int(message.text.split()[1])
        count = max(1, min(3, count))  # Ограничение 1-3
    except (IndexError, ValueError):
        count = 1

    user = message.reply_to_message.from_user
    new_count = warn_manager.remove_warn(user.id, count)
    
    await message.answer(
        f"✅ Снято {count} варн(а) с {user.full_name}. "
        f"Теперь у него {new_count}/5."
    )

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