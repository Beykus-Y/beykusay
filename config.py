import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = os.getenv('ADMIN_ID')
    MAX_MESSAGE_LENGTH = int(os.getenv('MAX_MESSAGE_LENGTH', 4000))
    MAX_HISTORY_LENGTH = int(os.getenv('MAX_HISTORY_LENGTH', 6))  # Добавить в .env
    AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', 20))
    RSS_MAPPING = {
        # ===== Технологии =====
        "технологии": [
            os.getenv("RSS_TECH"),          # Хабрахабр
            os.getenv("RSS_PROGRAMMING"),   # Tproger
            os.getenv("RSS_GADGETS")        # iGuides
        ],
        
        # ===== Наука =====
        "наука": [
            os.getenv("RSS_SCIENCE"),       # N+1
            os.getenv("RSS_SPACE"),         # Kosmolenta
            os.getenv("RSS_BIOLOGY")        # Элементы.ру
        ],
        
        # ===== Спорт =====
        "спорт": [
            os.getenv("RSS_SPORTS"),        # Sports.ru
            os.getenv("RSS_FOOTBALL")       # Чемпионат
        ],
        
        # ===== Игры =====
        "игры": [
            os.getenv("RSS_GAMING"),        # Stopgame
            os.getenv("RSS_ESPORTS")        # Cybersport.ru
        ],
        
        # ===== Финансы =====
        "финансы": [
            os.getenv("RSS_FINANCE"),       # Банки.ру
            os.getenv("RSS_ECONOMY")        # РБК
        ],
        
        # ===== Кино =====
        "кино": [
            os.getenv("RSS_MOVIES"),        # Film.ru
            os.getenv("RSS_CINEMA")         # Кино-Театр.ру
        ]
    }
    RSS_SOURCES = RSS_MAPPING

config = Config()