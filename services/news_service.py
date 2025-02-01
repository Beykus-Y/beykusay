import logging
from datetime import datetime
from typing import Dict, List, Any
import json
from config import config
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from pathlib import Path 
import feedparser
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, file_path: str = "data/subscriptions.json"):
        self.file_path = Path(file_path)
        self.subscriptions: Dict[int, Dict[str, Any]] = {}
        self.rss_sources = config.RSS_SOURCES
        self.sent_guids = set()
        self._guids_file = Path("data/sent_guids.json") 
        self._init_storage()
        self._load_data()
        self._load_sent_guids()
        logger.info("NewsService initialized")

    def _init_storage(self):
        """Создает необходимые файлы и директории"""
        Path("data").mkdir(exist_ok=True)
        self._guids_file.touch(exist_ok=True)
        self.file_path.touch(exist_ok=True)

    def _load_sent_guids(self):
        """Загружает историю отправленных GUID"""
        try:
            with open(self._guids_file, "r", encoding="utf-8") as f:
                self.sent_guids = set(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load GUIDs: {e}")

    def _save_sent_guids(self):
        """Сохраняет историю GUID в файл"""
        try:
            with open(self._guids_file, "w", encoding="utf-8") as f:
                json.dump(list(self.sent_guids), f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save GUIDs: {e}")

    def _load_data(self):
        """Загружает данные подписок"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.subscriptions = {
                    int(k): v for k, v in json.load(f).items()
                }
            logger.info(f"Loaded {len(self.subscriptions)} subscriptions")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            self.subscriptions = {}

    def _save_data(self):
        """Сохраняет данные подписок"""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.subscriptions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")

    def add_subscription(self, channel_id: int, topics: list, schedule: list):
        """Добавляет новую подписку"""
        self.subscriptions[channel_id] = {
            "topics": [t.strip() for t in topics if t.strip()],
            "schedule": schedule,
            "last_post": None
        }
        self._save_data()
        logger.info(f"Added subscription for channel {channel_id}")

    async def process_scheduled_posts(self, bot: Bot):
        """Обрабатывает запланированные публикации"""
        try:
            now = datetime.now().strftime("%H:%M")
            logger.debug(f"Checking schedule at {now}")
            
            for channel_id, settings in self.subscriptions.copy().items():
                if now in settings["schedule"] and settings["last_post"] != now:
                    logger.info(f"Processing channel {channel_id} at {now}")
                    await self._process_channel(bot, channel_id, settings, now)

        except Exception as e:
            logger.error(f"Critical error: {str(e)}", exc_info=True)

    async def _process_channel(self, bot: Bot, channel_id: int, settings: dict, now: str):
        """Обрабатывает публикации для конкретного канала"""
        try:
            for topic in settings["topics"]:
                news_items = await self.fetch_news(topic)
                if not news_items:
                    logger.warning(f"No news found for topic '{topic}'")
                    continue
                
                for news in news_items:
                    await self._send_news(bot, channel_id, news)

            settings["last_post"] = now
            self._save_data()

        except TelegramForbiddenError:
            logger.error(f"Bot was removed from channel {channel_id}")
            self.remove_subscription(channel_id)
        except TelegramBadRequest as e:
            logger.error(f"Telegram API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")

    async def _send_news(self, bot: Bot, channel_id: int, news: dict):
        """Отправляет новость в канал"""
        hashtags = " ".join(news["hashtags"])
        text = (
            f"📰 *{news['title']}*\n\n"
            f"{news['content']}\n\n"
            f"[Read more]({news['link']})\n"
            f"{hashtags}"
        )

        try:
            if news["image"]:
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=news["image"],
                    caption=text[:1024],
                    parse_mode="Markdown"
                )
            else:
                await self._send_fallback(bot, channel_id, text)
        except Exception as e:
            logger.error(f"Failed to send photo: {str(e)}")
            await self._send_fallback(bot, channel_id, text)

    async def _send_fallback(self, bot: Bot, channel_id: int, text: str):
        """Отправляет текстовое сообщение, если не удалось отправить фото"""
        try:
            await bot.send_message(
                chat_id=channel_id,
                text=text[:4096],
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")

    async def fetch_news(self, topic: str) -> List[Dict]:
        """Получает новости по указанной теме"""
        try:
            logger.info(f"Поиск новостей по тегу: {topic}")
            rss_urls = config.RSS_MAPPING.get(topic.lower(), [])
            
            if not rss_urls:
                logger.error(f"Для тега '{topic}' нет RSS-лент")
                return []

            news_items = []
            for rss_url in rss_urls:
                if not rss_url:
                    logger.warning("Пропущен пустой URL")
                    continue

                news_items += await self._parse_rss(rss_url)

            # Сортировка и выбор последней новости
            news_items.sort(
                key=lambda x: x.get("published_parsed", datetime.min.timetuple()),
                reverse=True
            )
            return news_items[:1]

        except Exception as e:
            logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
            return []

    async def _parse_rss(self, rss_url: str) -> List[Dict]:
        """Парсит RSS-ленту"""
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                logger.error(f"RSS error ({rss_url}): {feed.bozo_exception}")
                return []

            new_entries = []
            for entry in feed.entries:
                guid = entry.get("id", entry.get("link", str(datetime.now())))
                if guid not in self.sent_guids:
                    new_entries.append((entry, guid))

            return [self._process_entry(entry, guid) for entry, guid in new_entries[:5]]

        except Exception as e:
            logger.error(f"Ошибка парсинга {rss_url}: {str(e)}")
            return []

    def _process_entry(self, entry, guid: str) -> Dict:
        """Обрабатывает отдельную RSS-запись"""
        try:
            soup = BeautifulSoup(entry.description, "html.parser")
            
            # Поиск изображения
            img_tag = soup.find("img")
            image_url = img_tag["src"] if img_tag else ""
            
            # Fallback для медиа-контента
            if not image_url and hasattr(entry, "media_content"):
                image_url = entry.media_content[0]["url"]

            # Очистка текста
            text = re.sub(r'<a\b[^>]*>Читать далее</a>', '', entry.description)
            clean_text = BeautifulSoup(text, "html.parser").get_text().strip()
            
            # Хештеги
            hashtags = []
            if hasattr(entry, "tags"):
                hashtags = ["#" + tag.term.replace(" ", "_") for tag in entry.tags]
            elif hasattr(entry, "category"):
                hashtags = ["#" + entry.category.replace(" ", "_")]

            # Добавляем GUID в историю
            self.sent_guids.add(guid)
            self._save_sent_guids()

            return {
                "title": entry.title,
                "content": clean_text,
                "image": image_url,
                "link": entry.link,
                "hashtags": hashtags,
                "published_parsed": entry.get("published_parsed", datetime.min.timetuple())
            }

        except Exception as e:
            logger.error(f"Ошибка обработки новости: {str(e)}")
            return {}

    def remove_subscription(self, channel_id: int):
        """Удаляет подписку канала"""
        if channel_id in self.subscriptions:
            del self.subscriptions[channel_id]
            self._save_data()
            logger.info(f"Removed subscription for channel {channel_id}")

news_service = NewsService()