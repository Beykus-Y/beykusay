from aiogram.filters import BaseFilter
from aiogram.types import Message

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in ["group", "supergroup"]:
            print("❌ Команда вызвана не в группе")
            return False

        try:
            member = await message.bot.get_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id
            )
            print(f"Статус пользователя {message.from_user.id}: {member.status}")
            return member.status in ["administrator", "creator"]
        except Exception as e:
            print(f"Ошибка проверки прав: {e}")
            return False