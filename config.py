# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "db.sqlite3")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Добавь его в .env или в переменные окружения.")
