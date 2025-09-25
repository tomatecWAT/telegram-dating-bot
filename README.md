Telegram Dating Bot

Minimal dating bot built with aiogram 3.x and sqlite.

Setup

1. Create a virtualenv and install dependencies:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. Create a `.env` in the project root with your bot token:

```
BOT_TOKEN=123456:ABC-DEF
```

Run

```powershell
python bot.py
```

Notes

- Database file `db.sqlite3` will be created in the project root by default.
- `config.require_bot_token()` is called at runtime so importing modules won't raise during static checks.
- This is a minimal example. Consider adding persistent state for viewing profiles and handling concurrent bot restarts.
