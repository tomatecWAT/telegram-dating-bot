# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Bot token may be missing during static analysis; guard runtime code that imports this module.
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Database path can be overriden via env var; keep default in project root
DB_PATH = os.getenv("DB_PATH", "db.sqlite3")

# Do not raise on import to allow offline linting/tests; raise when attempting to run the bot.
def require_bot_token():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Добавь его в .env или в переменные окружения.")
