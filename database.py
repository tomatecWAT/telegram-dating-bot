import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from config import DB_PATH


def get_connection():
    # Allow connections from different threads and return Row objects for
    # nicer attribute access (row['field_name']). Using Row keeps callers
    # backwards-compatible with tuple-index access while improving clarity.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ========== Инициализация ==========
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Пользователи
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        gender TEXT,
        age INTEGER,
        city TEXT,
        target TEXT,
        bio TEXT,
        photo TEXT
    )
    """)

    # Лайки
    cur.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        action TEXT CHECK(action IN ('like', 'dislike')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Матчи
    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1 INTEGER,
        user2 INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# ========== Пользователи ==========
def add_user(telegram_id, gender, age, city, target, bio, photo):
    # Normalize some fields and ensure age is stored as integer when possible.
    try:
        age_int = int(age) if age is not None and str(age).strip() != "" else None
    except Exception:
        age_int = None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO users (telegram_id, gender, age, city, target, bio, photo)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (telegram_id, gender, age_int, city, target, bio, photo))
    conn.commit()
    conn.close()


def get_user_by_telegram_id(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cur.fetchone()
    conn.close()
    return user


def update_user_field(telegram_id, field, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field} = ? WHERE telegram_id = ?", (value, telegram_id))
    conn.commit()
    conn.close()


# ========== Просмотр анкет ==========
def get_random_profile(current_user_id):
    """
    Возвращает случайную анкету, которую текущий пользователь не лайкал/дизлайкал за последние 9 дней.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM users
    WHERE telegram_id != ?
      AND telegram_id NOT IN (
          SELECT to_user FROM likes
          WHERE from_user = ?
            AND created_at > datetime('now', '-9 days')
      )
    ORDER BY RANDOM() LIMIT 1
    """, (current_user_id, current_user_id))

    profile = cur.fetchone()
    conn.close()
    return profile


# ========== Лайки и матчи ==========
def add_like(from_user, to_user, action="like"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO likes (from_user, to_user, action)
    VALUES (?, ?, ?)
    """, (from_user, to_user, action))
    conn.commit()
    conn.close()


def check_match(user1, user2):
    """
    Проверяет, есть ли взаимный лайк. Если да — создаёт запись в matches.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT 1 FROM likes
    WHERE from_user = ? AND to_user = ? AND action = 'like'
    """, (user1, user2))
    like1 = cur.fetchone()

    cur.execute("""
    SELECT 1 FROM likes
    WHERE from_user = ? AND to_user = ? AND action = 'like'
    """, (user2, user1))
    like2 = cur.fetchone()

    if like1 and like2:
        # Normalize ordering so one match row represents a pair.
        a, b = sorted((user1, user2))
        # Avoid duplicate match rows.
        cur.execute("SELECT 1 FROM matches WHERE user1 = ? AND user2 = ?", (a, b))
        exists = cur.fetchone()
        if not exists:
            cur.execute("INSERT INTO matches (user1, user2) VALUES (?, ?)", (a, b))
            conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def get_matches_for_user(telegram_id):
    """
    Получает список матчей для конкретного пользователя.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM matches
    WHERE user1 = ? OR user2 = ?
    """, (telegram_id, telegram_id))
    matches = cur.fetchall()
    conn.close()
    return matches



# Показать "следующую" анкету для пользователя (простое правило: первая, которую user ещё не лайкал/не сам)
def get_next_profile_for(telegram_id: int) -> Optional[tuple]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.*
            FROM users u
            WHERE u.telegram_id != ?
              AND u.telegram_id NOT IN (
                  SELECT to_user FROM likes WHERE from_user = ?
              )
            ORDER BY u.id
            LIMIT 1
        """, (telegram_id, telegram_id))
        return cur.fetchone()