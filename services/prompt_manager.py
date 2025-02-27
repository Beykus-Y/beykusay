# services/prompt_manager.py
import json
from pathlib import Path
from typing import Dict, Optional
from enum import Enum
from services.context_manager import reset_chat_context

PROMPTS_FILE = Path(__file__).resolve().parent.parent / "data" / "chat_settings.json"

class AIMode(Enum):
    DEFAULT = "default"
    PRO = "pro"

class GeminiModel(Enum):
    FLASH = "gemini-2.0-flash"
    FLASH_LITE = "gemini-2.0-flash-lite"
    PRO_EXP = "gemini-2.0-pro-exp-02-05"
    FLASH_THINKING = "gemini-2.0-flash-thinking-exp-01-21"
    FLASH_8B = "gemini-1.5-flash-8b"

class ChatSettings:
    def __init__(self, prompt: str, ai_mode: AIMode = AIMode.DEFAULT, gemini_model: GeminiModel = None):
        self.prompt = prompt
        self.ai_mode = ai_mode
        self.gemini_model = gemini_model

    def to_dict(self):
        return {
            "prompt": self.prompt,
            "ai_mode": self.ai_mode.value,
            "gemini_model": self.gemini_model.value if self.gemini_model else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            prompt=data.get("prompt", ""),
            ai_mode=AIMode(data.get("ai_mode", AIMode.DEFAULT.value)),
            gemini_model=GeminiModel(data["gemini_model"]) if data.get("gemini_model") else None
        )

class PromptManager:
    def __init__(self):
        self.default_prompt = self._load_default_prompt()
        self.global_prompt = self._load_global_prompt()
        self.chat_settings: Dict[str, ChatSettings] = {}
        self._load_settings()

    def _load_settings(self):
        try:
            PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not PROMPTS_FILE.exists():
                self._save_settings()
                return
                
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.chat_settings = {
                    chat_id: ChatSettings.from_dict(settings)
                    for chat_id, settings in data.items()
                }
        except Exception:
            self.chat_settings = {}

    def _save_settings(self):
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            data = {
                chat_id: settings.to_dict()
                for chat_id, settings in self.chat_settings.items()
            }
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_default_prompt(self) -> str:
        try:
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return " "

    def _load_global_prompt(self) -> str:
        try:
            with open("global_prompt.txt", "r", encoding="utf-8") as f:
                return f.read().strip() + "\n\n"
        except Exception:
            return ""

    def get_combined_prompt(self, chat_id: int) -> str:
        global_prompt = self._load_global_prompt()
        settings = self.chat_settings.get(str(chat_id))
        custom_prompt = settings.prompt if settings else self.default_prompt
        return global_prompt + custom_prompt

    def get_settings(self, chat_id: int) -> ChatSettings:
        return self.chat_settings.get(str(chat_id), ChatSettings(self.default_prompt))

    def set_prompt(self, chat_id: int, prompt: str):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.chat_settings:
            self.chat_settings[chat_id_str] = ChatSettings(prompt)
        else:
            self.chat_settings[chat_id_str].prompt = prompt
        self._save_settings()
        reset_chat_context(chat_id)

    def set_ai_mode(self, chat_id: int, mode: AIMode):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.chat_settings:
            self.chat_settings[chat_id_str] = ChatSettings(self.default_prompt, mode)
        else:
            self.chat_settings[chat_id_str].ai_mode = mode
        self._save_settings()

    def set_gemini_model(self, chat_id: int, model: GeminiModel):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.chat_settings:
            self.chat_settings[chat_id_str] = ChatSettings(self.default_prompt, AIMode.PRO, model)
        else:
            self.chat_settings[chat_id_str].gemini_model = model
            self.chat_settings[chat_id_str].ai_mode = AIMode.PRO
        self._save_settings()

    def reset_settings(self, chat_id: int):
        chat_id_str = str(chat_id)
        if chat_id_str in self.chat_settings:
            del self.chat_settings[chat_id_str]
            self._save_settings()
        self.default_prompt = self._load_default_prompt()
        reset_chat_context(chat_id)

prompt_manager = PromptManager()