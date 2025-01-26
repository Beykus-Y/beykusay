import sys
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ContentType
from aiogram.fsm.storage.memory import MemoryStorage
from services.news_service import news_service
from handlers.news_setup import router as news_router  
from states import NewsSetupStates
from handlers.admin import admin_router
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from middlewares.antiflood import AntiFloodMiddleware
from middlewares.stats import StatsMiddleware
from handlers import admin, common
from filters.admin import IsAdminFilter

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Middleware
    dp.update.outer_middleware(StatsMiddleware())
    dp.update.outer_middleware(AntiFloodMiddleware())

    # Route
    dp.include_router(news_router)
    dp.include_router(admin_router)
    
    # Регистрация обработчиков
    dp.message.register(admin.ban_user, Command('ban'), IsAdminFilter())
    dp.message.register(admin.unban_user, Command('unban'), IsAdminFilter())
    dp.message.register(admin.warn_user, Command('warn'), IsAdminFilter())
    dp.message.register(admin.unwarn_user, Command('unwarn'), IsAdminFilter())
    dp.message.register(admin.delete_message, Command('del'), IsAdminFilter())
    dp.message.register(admin.show_stats, Command('stats'))
    dp.message.register(admin.charts_command, Command('charts')),
    dp.message.register(admin.set_prompt, Command('set_prompt'), IsAdminFilter())
    dp.message.register(admin.reset_prompt, Command('reset_prompt'), IsAdminFilter())
    dp.message.register(admin.clear_history, Command('clear'), IsAdminFilter())
    dp.message.register(admin.show_warns, Command('warns'), IsAdminFilter())
    dp.message.register(
        common.handle_message,
        F.content_type == ContentType.TEXT,
        F.chat.type.in_({"group", "supergroup"})
    )

    asyncio.create_task(news_scheduler(bot))

    await dp.start_polling(bot)

async def news_scheduler(bot: Bot):
    while True:
        await asyncio.sleep(60)  # Проверка каждую минуту
        await news_service.process_scheduled_posts(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
