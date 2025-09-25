# database.py
import sqlite3
from typing import Optional, Dict, Any
from config import DB_PATH

def get_connection():
    # ensure row access by name
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    sql_users = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        gender TEXT,
        age INTEGER,
        city TEXT,
        target TEXT,
        bio TEXT,
        photo TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    sql_likes = """
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER NOT NULL,
        to_user INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (from_user) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (to_user) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE (from_user, to_user)
    );
    """
    sql_matches = """
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1 INTEGER NOT NULL,
        user2 INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user1) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (user2) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE (user1, user2)
    );
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executescript(sql_users + sql_likes + sql_matches)
        conn.commit()

# USER CRUD
def upsert_user_from_telegram(telegram_id: int, **fields) -> int:
    """
    Вставляет или обновляет запись пользователя по telegram_id.
    Возвращает id (PK) записи в users.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        # пробуем найти
        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        if row:
            user_id = row["id"]
            # обновляем переданные поля
            if fields:
                cols = ", ".join(f"{k}=?" for k in fields.keys())
                values = list(fields.values()) + [telegram_id]
                cur.execute(f"UPDATE users SET {cols} WHERE telegram_id = ?", values)
                conn.commit()
            return user_id
        else:
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            values = list(fields.values())
            # insert with telegram_id plus fields
            sql = f"INSERT INTO users (telegram_id, {cols}) VALUES (?, {placeholders})"
            cur.execute(sql, [telegram_id] + values)
            conn.commit()
            return cur.lastrowid

def get_user_by_telegram_id(telegram_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return cur.fetchone()

def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cur.fetchone()

# Показать "следующую" анкету для пользователя (простое правило: первая, которую user ещё не лайкал/не сам)
def get_next_profile_for(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.*
            FROM users u
            WHERE u.id != ?
              AND u.id NOT IN (
                  SELECT to_user FROM likes WHERE from_user = ?
              )
            ORDER BY u.id
            LIMIT 1
        """, (user_id, user_id))
        return cur.fetchone()

# Лайк
def add_like(from_user: int, to_user: int) -> bool:
    """
    Добавляем лайк; возвращаем True если добавлено, False если уже был.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO likes (from_user, to_user) VALUES (?, ?)",
                (from_user, to_user)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

# Проверка на взаимный лайк -> если есть, создать запись в matches (user1 < user2)
def check_and_create_match_if_any(a_id: int, b_id: int) -> Optional[int]:
    with get_connection() as conn:
        cur = conn.cursor()
        # проверяем есть ли обратный лайк
        cur.execute(
            "SELECT 1 FROM likes WHERE from_user = ? AND to_user = ?",
            (b_id, a_id)
        )
        if cur.fetchone():
            user1, user2 = (a_id, b_id) if a_id < b_id else (b_id, a_id)
            try:
                cur.execute(
                    "INSERT INTO matches (user1, user2) VALUES (?, ?)",
                    (user1, user2)
                )
                conn.commit()
                return cur.lastrowid
            except sqlite3.IntegrityError:
                # матч уже существует
                return None
        return None

# Полезные удобные функции
def get_profile_payload(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "telegram_id": row["telegram_id"],
        "gender": row["gender"],
        "age": row["age"],
        "city": row["city"],
        "target": row["target"],
        "bio": row["bio"],
        "photo": row["photo"],
    }
