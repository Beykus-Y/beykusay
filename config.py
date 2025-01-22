import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = os.getenv('ADMIN_ID')
    MAX_MESSAGE_LENGTH = int(os.getenv('MAX_MESSAGE_LENGTH', 4000))
    MAX_HISTORY_LENGTH = int(os.getenv('MAX_HISTORY_LENGTH', 6))  # Добавить в .env
    AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', 20))

config = Config()