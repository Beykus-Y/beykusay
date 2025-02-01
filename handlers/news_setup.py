from aiogram import F, types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from services.news_service import news_service
from states import NewsSetupStates
from config import config
import logging
import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("news_setup"))
async def start_setup(message: types.Message, state: FSMContext):
    """Начало настройки автоновостей"""
    try:
        await message.answer(
            "📰 Настройка автоновостей:\n"
            "1. Добавьте бота в администраторы вашего канала\n"
            "2. Пришлите @username вашего канала",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
            ])
        )
        await state.set_state(NewsSetupStates.waiting_channel)
        logger.info(f"Начата настройка для пользователя {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка старта настройки: {str(e)}")
        await message.answer("❌ Произошла ошибка, попробуйте позже.")

@router.callback_query(F.data == "cancel")
async def cancel_setup(callback: types.CallbackQuery, state: FSMContext):
    """Обработка отмены настройки"""
    await state.clear()
    await callback.message.answer("❌ Настройка отменена.")
    logger.info(f"Пользователь {callback.from_user.id} отменил настройку")

@router.message(NewsSetupStates.waiting_channel)
async def process_channel(message: types.Message, state: FSMContext):
    """Обработка username канала"""
    try:
        channel_username = message.text.strip().lstrip('@')
        logger.debug(f"Получен канал: {channel_username}")
        
        chat = await message.bot.get_chat(f"@{channel_username}")
        admins = await message.bot.get_chat_administrators(chat.id)
        bot_id = (await message.bot.get_me()).id
        user_id = message.from_user.id
        
        # Проверка является ли пользователь администратором канала
        if not any(admin.user.id == user_id for admin in admins):
            logger.warning(f"Пользователь {user_id} не является администратором канала {channel_username}")
            await message.answer("❌ Вы должны быть администратором канала для его настройки!")
            return
        
        # Проверка является ли бот администратором канала
        if not any(admin.user.id == bot_id for admin in admins):
            logger.warning(f"Бот не админ в канале {channel_username}")
            await message.answer("❌ Бот не является администратором канала!")
            return
            
        await state.update_data(channel=chat.id)
        await message.answer(
            "✅ Канал подтвержден. Укажите темы через запятую:\n" 
            f"Доступные темы: {', '.join(config.RSS_MAPPING.keys())}"
        )
        await state.set_state(NewsSetupStates.waiting_topics)
        logger.info(f"Канал {channel_username} подтвержден")
        
    except Exception as e:
        logger.error(f"Ошибка проверки канала: {str(e)}")
        await message.answer("❌ Канал не найден или бот не имеет прав!")

@router.message(NewsSetupStates.waiting_topics)
async def process_topics(message: types.Message, state: FSMContext):
    """Обработка выбора тематик"""
    try:
        user_tags = [t.strip().lower() for t in message.text.split(",")]
        valid_tags = []
        invalid_tags = []
        
        # Фильтрация тегов
        for tag in user_tags:
            if tag in config.RSS_MAPPING:
                valid_tags.append(tag)
            else:
                invalid_tags.append(tag)
        
        if invalid_tags:
            await message.answer(
                f"❌ Неизвестные теги: {', '.join(invalid_tags)}\n"
                f"Доступные теги: {', '.join(config.RSS_MAPPING.keys())}"
            )
            return
            
        if not valid_tags:
            await message.answer("❌ Не указано ни одного валидного тега!")
            return
            
        await state.update_data(tags=valid_tags)
        await message.answer(
            "⏰ Укажите время публикаций (например: 09:00, 18:00)\n"
            "Формат: ЧЧ:MM",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Каждый час", callback_data="default_schedule")]
            ])
        )
        await state.set_state(NewsSetupStates.waiting_schedule)
        logger.info(f"Валидные теги: {valid_tags}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки тем: {str(e)}")
        await message.answer("❌ Ошибка обработки тем, попробуйте снова.")

@router.message(NewsSetupStates.waiting_schedule)
async def process_schedule(message: types.Message, state: FSMContext):
    """Обработка пользовательского расписания"""
    try:
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
        raw_times = message.text.split(",")
        normalized = []
        errors = []

        for raw_time in raw_times:
            time_str = raw_time.strip().replace(" ", "").replace(";", ":")
            if not time_pattern.match(time_str):
                errors.append(raw_time.strip())
                continue
                
            try:
                hours, minutes = map(int, time_str.split(":"))
                normalized_time = f"{hours:02d}:{minutes:02d}"
                normalized.append(normalized_time)
            except ValueError:
                errors.append(raw_time.strip())

        if errors:
            error_examples = "\n".join([f"• {e} → Неверный формат" for e in errors[:3]])
            await message.answer(
                f"❌ Ошибки в формате времени:\n{error_examples}\n"
                "✅ Пример: 09:00, 18:30, 23:59",
                parse_mode="Markdown"
            )
            return

        data = await state.get_data()
        news_service.add_subscription(
            channel_id=data["channel"],
            topics=data["tags"],
            schedule=normalized
        )
        
        await message.answer(
            "✅ Настройки сохранены!\n"
            f"• Темы: {', '.join(data['tags'])}\n"
            f"• Время: {', '.join(normalized)}"
        )
        await state.clear()
        
    except KeyError:
        await message.answer("❌ Ошибка: данные повреждены. Начните заново.")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}", exc_info=True)
        await message.answer("❌ Внутренняя ошибка. Попробуйте позже.")

@router.callback_query(F.data == "default_schedule")
async def set_default_schedule(callback: types.CallbackQuery, state: FSMContext):
    """Установка расписания по умолчанию"""
    try:
        hourly_schedule = [f"{hour:02d}:00" for hour in range(24)]
        await state.update_data(schedule=hourly_schedule)
        data = await state.get_data()
        
        if not all(key in data for key in ("channel", "tags")):
            logger.error("Отсутствуют данные в состоянии")
            await callback.message.answer("❌ Ошибка: сессия повреждена.")
            return
            
        rss_urls = []
        for tag in data["tags"]:
            rss_urls.extend(config.RSS_MAPPING.get(tag, []))
            
        news_service.add_subscription(
            channel_id=data["channel"],
            rss_urls=list(set(rss_urls)),
            schedule=hourly_schedule
        )
        
        await callback.message.answer(
            "✅ Настройки сохранены!\n"
            f"• Темы: {', '.join(data['tags'])}\n"
            f"• Время: каждый час"
        )
        logger.info(f"Сохранено расписание для канала {data['channel']}")
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await callback.message.answer("❌ Ошибка при сохранении!")
    finally:
        await state.clear()