import json
from pathlib import Path
from typing import Dict, Tuple

WARNS_DIR = Path(__file__).resolve().parent.parent / "stats"  # Используем ту же папку
WARNS_FILE = WARNS_DIR / "warns.json"

class WarnManager:
    def __init__(self):
        self.warns: Dict[Tuple[int, int], int] = {}  # (chat_id, user_id): count
        self._init_storage()  # Добавляем инициализацию хранилища
        self._load_warns()
        print("Инициализирован WarnManager")

    def _init_storage(self):
        """Создает файл и директорию при необходимости"""
        WARNS_DIR.mkdir(parents=True, exist_ok=True)
        if not WARNS_FILE.exists():
            with open(WARNS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
            print("Создан новый файл варнов")

    # Остальные методы без изменений
    def _load_warns(self):
        try:
            if WARNS_FILE.stat().st_size == 0:
                self.warns = {}
                print("Файл варнов пуст")
                return

            with open(WARNS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.warns = {
                    (int(chat_id), int(user_id)): count 
                    for key, count in data.items()
                    for chat_id, user_id in [key.split(",")]
                }
            print(f"Загружено варнов: {len(self.warns)}")
        except Exception as e:
            print(f"Ошибка загрузки варнов: {str(e)}")
            self.warns = {}

    def _save_warns(self):
        try:
            with open(WARNS_FILE, "w", encoding="utf-8") as f:
                serialized = {f"{c},{u}": count for (c, u), count in self.warns.items()}
                json.dump(serialized, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения варнов: {str(e)}")

    def add_warn(self, chat_id: int, user_id: int) -> int:
        key = (chat_id, user_id)
        self.warns[key] = self.warns.get(key, 0) + 1
        self._save_warns()
        return self.warns[key]

    def remove_warn(self, chat_id: int, user_id: int, count: int = 1) -> int:
        key = (chat_id, user_id)
        current = self.warns.get(key, 0)
        new_count = max(0, current - count)
        
        if new_count == 0:
            if key in self.warns:
                del self.warns[key]
        else:
            self.warns[key] = new_count
            
        self._save_warns()
        return new_count

    def get_warns(self, chat_id: int, user_id: int) -> int:
        return self.warns.get((chat_id, user_id), 0)

    def get_chat_warns(self, chat_id: int) -> Dict[int, int]:
        return {user_id: count for (c_id, user_id), count in self.warns.items() if c_id == chat_id}

warn_manager = WarnManager()