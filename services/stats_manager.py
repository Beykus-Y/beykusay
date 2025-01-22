import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

STATS_DIR = Path("stats")
STATS_FILE = STATS_DIR / "stats.json"

class StatsManager:
    def __init__(self):
        self.stats: Dict[int, int] = {}
        self._init_storage()
        self._load_stats()
        print("Инициализирован StatsManager")

    def _init_storage(self):
        print(f"Проверка директории: {STATS_DIR.absolute()}")
        STATS_DIR.mkdir(parents=True, exist_ok=True)
        if not STATS_FILE.exists():
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
            print("Создан новый файл статистики")

    def _load_stats(self):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                self.stats = {int(k): v for k, v in raw_data.items()}
            print(f"Загружено записей: {len(self.stats)}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Ошибка загрузки: {str(e)}")
            self.stats = {}

    def _save_stats(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
            print(f"Успешно сохранено {len(self.stats)} записей")
        except Exception as e:
            print(f"Критическая ошибка сохранения: {str(e)}")

    def update_user(self, user_id: int):
        self.stats[user_id] = self.stats.get(user_id, 0) + 1
        print(f"Обновление статистики для {user_id}: {self.stats[user_id]}")
        self._save_stats()

    def get_top_users(self, limit: int = 10) -> List[Tuple[int, int]]:
        return sorted(self.stats.items(), key=lambda x: x[1], reverse=True)[:limit]

stats_manager = StatsManager()