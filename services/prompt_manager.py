# services/prompt_manager.py
import json
from pathlib import Path
from typing import Dict, Optional
from services.context_manager import reset_chat_context

PROMPTS_FILE = Path(__file__).resolve().parent.parent / "data" / "chat_prompts.json"

class PromptManager:
    def __init__(self):
        self.default_prompt = self._load_default_prompt()
        self.global_prompt = self._load_global_prompt()
        self.chat_prompts: Dict[int, str] = {}
        self._load_prompts()

    def _load_default_prompt(self) -> str:
        try:
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return " "

    def _load_prompts(self):
        try:
            PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not PROMPTS_FILE.exists():
                self._save_prompts()
                return
                
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                self.chat_prompts = json.load(f)
        except Exception:
            self.chat_prompts = {}

    def _load_global_prompt(self) -> str:
        try:
            with open("global_prompt.txt", "r", encoding="utf-8") as f:
                return f.read().strip() + "\n\n"
        except Exception:
            return ""

    def get_combined_prompt(self, chat_id: int) -> str:
        global_prompt = self._load_global_prompt()
        custom_prompt = self.chat_prompts.get(str(chat_id), self.default_prompt)
        return global_prompt + custom_prompt

    def _save_prompts(self):
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.chat_prompts, f, ensure_ascii=False, indent=2)

    def get_prompt(self, chat_id: int) -> str:
        return self.chat_prompts.get(str(chat_id), self.default_prompt)

    def set_prompt(self, chat_id: int, prompt: str):
        self.chat_prompts[str(chat_id)] = prompt
        self._save_prompts()
        reset_chat_context(chat_id)

    def reset_prompt(self, chat_id: int):
        chat_id_str = str(chat_id)
        if chat_id_str in self.chat_prompts:
            del self.chat_prompts[chat_id_str]
            self._save_prompts()
        self.default_prompt = self._load_default_prompt()
        reset_chat_context(chat_id)

prompt_manager = PromptManager()