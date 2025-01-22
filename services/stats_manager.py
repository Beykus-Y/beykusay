# services/stats_manager.py
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

STATS_DIR = Path(__file__).resolve().parent.parent / "stats"
STATS_FILE = STATS_DIR / "stats.json"

class StatsManager:
    def __init__(self):
        self.stats: Dict[Tuple[int, int], int] = {}  # (chat_id, user_id): count
        print(f"Путь к файлу статистики: {STATS_FILE.absolute()}")
        self._init_storage()
        self._load_stats()
        print("Инициализирован StatsManager")

    def _init_storage(self):
        STATS_DIR.mkdir(parents=True, exist_ok=True)
        if not STATS_FILE.exists():
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_stats(self):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.stats = {
                    (int(chat_id), int(user_id)): count 
                    for (chat_id, user_id), count in data.items()
                }
        except Exception as e:
            print(f"Ошибка загрузки: {str(e)}")
            self.stats = {}

    def _save_stats(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                # Конвертируем кортежи ключей в строки для JSON
                serializable_data = {
                    f"{chat_id},{user_id}": count 
                    for (chat_id, user_id), count in self.stats.items()
                }
                json.dump(serializable_data, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {str(e)}")

    def update_user(self, chat_id: int, user_id: int):
        key = (chat_id, user_id)
        self.stats[key] = self.stats.get(key, 0) + 1
        self._save_stats()

    def get_chat_stats(self, chat_id: int) -> List[Tuple[int, int]]:
        return sorted(
            [(user_id, count) for (c_id, user_id), count in self.stats.items() if c_id == chat_id],
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Топ-10 пользователей

stats_manager = StatsManager()