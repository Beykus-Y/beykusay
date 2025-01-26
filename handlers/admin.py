from aiogram import types, Bot
from services.ai import reset_chat_context
from services.warn_manager import warn_manager
from aiogram.filters import Command
from aiogram.types import User
from aiogram import Router
from services.stats_manager import stats_manager
import logging
from filters.admin import IsAdminFilter
from services.prompt_manager import prompt_manager
from services.context_manager import reset_chat_context
from services.news_service import news_service
from services.get_charts import show_charts_handler

logger = logging.getLogger(__name__) 

admin_router = Router()

async def check_target_is_admin(chat_id: int, user_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        logging.error(f"Ошибка проверки прав цели: {str(e)}")
        return False

async def show_warns(message: types.Message):
    chat_id = message.chat.id
    
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        warn_count = warn_manager.get_warns(chat_id, user.id)
        await message.answer(
            f"⚠️ Пользователь {user.full_name} имеет {warn_count}/5 варнов в этом чате."
        )
    else:
        # Показать все варны в чате
        warns = warn_manager.get_chat_warns(chat_id)
        if not warns:
            await message.answer("В этом чате пока нет варнов.")
            return
            
        warn_list = ["🚨 Список варнов в этом чате:"]
        for user_id, count in warns.items():
            try:
                user = await message.bot.get_chat(user_id)
                name = user.full_name
            except Exception:
                name = f"Пользователь #{user_id}"
                
            warn_list.append(f"• {name}: {count} варн(а)")
        
        await message.answer("\n".join(warn_list))

async def unwarn_user(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя!")
        return

    user = message.reply_to_message.from_user
    
    # Проверка, что цель не бот
    if user.is_bot:
        await message.answer("🚫 У бота нет варнов!")
        return
    
    if await check_target_is_admin(message.chat.id, user.id, message.bot):
        await message.answer("ℹ️ У администраторов нет варнов")
        return


    try:
        count = int(message.text.split()[1])
        count = max(1, min(3, count))
    except (IndexError, ValueError):
        count = 1

    new_count = warn_manager.remove_warn(message.chat.id, user.id, count)
    
    await message.answer(
        f"✅ Снято {count} варн(а) с {user.full_name}. "
        f"Теперь у него {new_count}/5."
    )

async def ban_user(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя!")
        return

    user = message.reply_to_message.from_user
    
    if user.is_bot:
        await message.answer("🚫 Нельзя забанить бота!")
        return
    
    if await check_target_is_admin(message.chat.id, user.id, message.bot):
        await message.answer("🚫 Нельзя забанить администратора!")
        return


    try:
        await message.chat.ban(user.id)
        await message.answer(f"🚨 Пользователь {user.full_name} забанен")
    except Exception as e:
        await message.answer(f"❌ Ошибка бана: {str(e)}")

async def unban_user(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя!")
        return

    user = message.reply_to_message.from_user
    
    # Проверка, что цель не бот
    if user.is_bot:
        await message.answer("🚫 Нельзя разбанить бота (он не был забанен)!")
        return
    
    if await check_target_is_admin(message.chat.id, user.id, message.bot):
        await message.answer("ℹ️ Пользователь не забанен")
        return

    try:
        await message.chat.unban(user.id)
        await message.answer(f"✅ Пользователь {user.full_name} разбанен")
    except Exception as e:
        await message.answer(f"❌ Ошибка разбана: {str(e)}")

async def warn_user(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя!")
        return

    user = message.reply_to_message.from_user
    
    # Проверка, что цель не бот
    if user.is_bot:
        await message.answer("🚫 Нельзя выдать варн боту!")
        return
    # Проверка, что цель не администратор
    if await check_target_is_admin(message.chat.id, user.id, message.bot):
        await message.answer("🚫 Нельзя выдать варн администратору!")
        return

    warn_count = warn_manager.add_warn(message.chat.id, user.id)
    await message.answer(
        f"⚠️ {user.full_name} получил предупреждение! Теперь у него {warn_count}/5 варнов."
    )
    
    if warn_count >= 5:
        await message.chat.ban(user.id)
        await message.answer(f"🚨 {user.full_name} забанен за 5 предупреждений!")
        warn_manager.remove_warn(message.chat.id, user.id, 5)

async def show_stats(message: types.Message):
    chat_id = message.chat.id
    top_users = stats_manager.get_chat_stats(chat_id)
    
    if not top_users:
        await message.answer("📊 Статистика для этого чата пока недоступна")
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
    chat_id = message.chat.id
    reset_chat_context(chat_id)
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

async def set_prompt(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение с новым промптом!")
        return
    
    new_prompt = message.reply_to_message.text
    prompt_manager.set_prompt(message.chat.id, new_prompt)
    await message.answer("✅ Системный промпт для этого чата обновлен!")
    reset_chat_context(message.chat.id)

async def reset_prompt(message: types.Message):
    prompt_manager.reset_prompt(message.chat.id)
    await message.answer("✅ Системный промпт сброшен до стандартного!")
    reset_chat_context(message.chat.id)

@admin_router.message(Command('charts'), IsAdminFilter())
async def charts_command(message: types.Message):
    await show_charts_handler(message)

@admin_router.message(Command('subscribe'),)
async def subscribe_topic(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажите тему: /subscribe tech")
        return
    
    topic = args[1]
    news_service.subscriptions[message.chat.id] = {"topics": [topic]}
    await message.answer(f"✅ Подписка на тему '{topic}' оформлена!")
