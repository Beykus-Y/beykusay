# services/warn_manager.py
import json
from pathlib import Path
from typing import Dict

WARNS_FILE = Path("stats") / "warns.json"

class WarnManager:
    def __init__(self):
        self.warns: Dict[int, int] = {}
        self._load_warns()

    def _load_warns(self):
        try:
            with open(WARNS_FILE, "r") as f:
                self.warns = {int(k): v for k, v in json.load(f).items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.warns = {}

    def _save_warns(self):
        with open(WARNS_FILE, "w") as f:
            json.dump(self.warns, f, indent=2)

    def add_warn(self, user_id: int):
        self.warns[user_id] = self.warns.get(user_id, 0) + 1
        self._save_warns()
        return self.warns[user_id]

    def remove_warn(self, user_id: int, count: int = 1):
        current = self.warns.get(user_id, 0)
        self.warns[user_id] = max(0, current - count)
        if self.warns[user_id] == 0:
            del self.warns[user_id]
        self._save_warns()
        return self.warns.get(user_id, 0)

warn_manager = WarnManager()