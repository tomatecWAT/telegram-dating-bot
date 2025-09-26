import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import math

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

    # Пользователи (добавлено поле name и координаты для фильтрации)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        gender TEXT,
        age INTEGER,
        city TEXT,
        latitude REAL,
        longitude REAL,
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

    # Фильтры пользователей
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        target_filters TEXT,  -- JSON строка с массивом целей
        distance_filter INTEGER,  -- расстояние в км
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Добавляем новые столбцы если их нет (миграция для существующих баз)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass  # столбец уже существует

    try:
        cur.execute("ALTER TABLE users ADD COLUMN latitude REAL")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE users ADD COLUMN longitude REAL")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# ========== Пользователи ==========
def add_user(telegram_id, name, gender, age, city, target, bio, photo, latitude=None, longitude=None):
    # Normalize some fields and ensure age is stored as integer when possible.
    try:
        age_int = int(age) if age is not None and str(age).strip() != "" else None
    except Exception:
        age_int = None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO users (telegram_id, name, gender, age, city, latitude, longitude, target, bio, photo)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (telegram_id, name, gender, age_int, city, latitude, longitude, target, bio, photo))
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


def update_user_coordinates(telegram_id, latitude, longitude):
    """Обновляет координаты пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET latitude = ?, longitude = ? WHERE telegram_id = ?", 
                (latitude, longitude, telegram_id))
    conn.commit()
    conn.close()


# ========== Фильтры ==========
def save_user_target_filters(telegram_id, target_filters: List[str]):
    """Сохраняет только фильтры по целям (Этап 1)"""
    import json
    
    print(f"\n========== SAVE_USER_TARGET_FILTERS ==========")
    print(f"DEBUG: Начало функции save_user_target_filters")
    print(f"DEBUG: telegram_id = {telegram_id} (тип: {type(telegram_id)})")
    print(f"DEBUG: target_filters = {target_filters} (тип: {type(target_filters)})")
    
    if not isinstance(telegram_id, int):
        print(f"ERROR: telegram_id должен быть int, получен {type(telegram_id)}")
        return False
    
    if not isinstance(target_filters, list):
        print(f"ERROR: target_filters должен быть list, получен {type(target_filters)}")
        return False
    
    # Проверяем входные данные
    if not target_filters:
        print("WARNING: target_filters пустой, используем все цели по умолчанию")
        target_filters = ["Дружба", "Общение", "Отношения", "Ничего серьезного", "Свидания"]
    
    try:
        target_filters_json = json.dumps(target_filters, ensure_ascii=False)
        print(f"DEBUG: target_filters_json = '{target_filters_json}'")
    except Exception as e:
        print(f"ERROR: Ошибка при преобразовании в JSON: {e}")
        return False
    
    try:
        print("DEBUG: Получаем соединение с базой данных...")
        conn = get_connection()
        cur = conn.cursor()
        print("DEBUG: Соединение получено успешно")
        
        # Проверяем, существует ли таблица
        print("DEBUG: Проверяем существование таблицы user_filters...")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_filters'")
        table_exists = cur.fetchone()
        
        if not table_exists:
            print("ERROR: Таблица user_filters НЕ СУЩЕСТВУЕТ!")
            print("ERROR: Необходимо запустить /create_filters_table или reset_db.py")
            conn.close()
            return False
        
        print("DEBUG: Таблица user_filters существует ✓")
        
        # Проверяем, существует ли запись
        print(f"DEBUG: Ищем существующую запись для telegram_id={telegram_id}...")
        cur.execute("SELECT id, target_filters, distance_filter FROM user_filters WHERE telegram_id = ?", (telegram_id,))
        existing = cur.fetchone()
        
        if existing:
            existing_dict = dict(existing)
            print(f"DEBUG: Найдена существующая запись: {existing_dict}")
            
            # Обновляем только цели, расстояние не трогаем
            print("DEBUG: Выполняем UPDATE...")
            cur.execute("""
            UPDATE user_filters 
            SET target_filters = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """, (target_filters_json, telegram_id))
            operation = "UPDATE"
        else:
            print("DEBUG: Записи не найдено, создаем новую...")
            # Создаем новую запись только с целями
            cur.execute("""
            INSERT INTO user_filters (telegram_id, target_filters, distance_filter, updated_at)
            VALUES (?, ?, NULL, CURRENT_TIMESTAMP)
            """, (telegram_id, target_filters_json))
            operation = "INSERT"
        
        # Проверяем количество затронутых строк
        rows_affected = cur.rowcount
        print(f"DEBUG: Операция {operation}: затронуто строк = {rows_affected}")
        
        if rows_affected == 0:
            print("ERROR: Ни одна строка не была изменена!")
            conn.close()
            return False
        
        # Коммитим изменения
        print("DEBUG: Выполняем COMMIT...")
        conn.commit()
        print("DEBUG: COMMIT выполнен успешно ✓")
        
        # Проверяем, что данные действительно сохранились
        print("DEBUG: Проверяем результат сохранения...")
        cur.execute("SELECT * FROM user_filters WHERE telegram_id = ?", (telegram_id,))
        saved_record = cur.fetchone()
        
        if saved_record:
            saved_dict = dict(saved_record)
            print(f"DEBUG: Проверка после сохранения: {saved_dict}")
            
            # Дополнительно проверяем JSON
            try:
                parsed_targets = json.loads(saved_record['target_filters'])
                print(f"DEBUG: Распарсенные цели: {parsed_targets}")
                
                if parsed_targets == target_filters:
                    print("DEBUG: Данные сохранены корректно ✓")
                else:
                    print(f"ERROR: Данные не совпадают! Ожидалось: {target_filters}, получено: {parsed_targets}")
                    conn.close()
                    return False
            except Exception as e:
                print(f"ERROR: Ошибка парсинга JSON: {e}")
                conn.close()
                return False
        else:
            print("ERROR: Запись не найдена после сохранения!")
            conn.close()
            return False
        
        conn.close()
        print(f"DEBUG: Цели сохранены успешно для пользователя {telegram_id} ✓")
        print(f"========== КОНЕЦ SAVE_USER_TARGET_FILTERS ==========\n")
        return True
        
    except Exception as e:
        print(f"ERROR: Критическая ошибка при сохранении целей: {e}")
        import traceback
        traceback.print_exc()
        print(f"========== ОШИБКА В SAVE_USER_TARGET_FILTERS ==========\n")
        return False


def save_user_distance_filter(telegram_id, distance_km: int):
    """Сохраняет фильтр по расстоянию (Этап 2)"""
    print(f"DEBUG: save_user_distance_filter вызвана для пользователя {telegram_id}")
    print(f"  distance_km: {distance_km}")
    print(f"  type(distance_km): {type(distance_km)}")
    
    distance_value = distance_km if distance_km is not None else None
    print(f"DEBUG: distance_value для сохранения: {distance_value}")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Проверяем, существует ли таблица
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_filters'")
        table_exists = cur.fetchone()
        if not table_exists:
            print("ERROR: Таблица user_filters НЕ СУЩЕСТВУЕТ!")
            conn.close()
            return False
        
        # Проверяем, существует ли запись
        cur.execute("SELECT id, target_filters, distance_filter FROM user_filters WHERE telegram_id = ?", (telegram_id,))
        existing = cur.fetchone()
        
        if existing:
            print(f"DEBUG: Найдена существующая запись: {dict(existing)}")
            # Обновляем расстояние, цели не трогаем
            cur.execute("""
            UPDATE user_filters 
            SET distance_filter = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """, (distance_value, telegram_id))
            print(f"DEBUG: Выполнен UPDATE расстояния для пользователя {telegram_id}")
        else:
            print("WARNING: Записи не найдено! Создаем новую только с расстоянием")
            # Создаем новую запись только с расстоянием (это странная ситуация)
            cur.execute("""
            INSERT INTO user_filters (telegram_id, target_filters, distance_filter, updated_at)
            VALUES (?, NULL, ?, CURRENT_TIMESTAMP)
            """, (telegram_id, distance_value))
            print(f"DEBUG: Выполнен INSERT только с расстоянием для пользователя {telegram_id}")
        
        # Проверяем количество затронутых строк
        rows_affected = cur.rowcount
        print(f"DEBUG: Количество затронутых строк: {rows_affected}")
        
        if rows_affected == 0:
            print("ERROR: Ни одна строка не была изменена!")
            conn.close()
            return False
        
        conn.commit()
        print("DEBUG: COMMIT расстояния выполнен успешно")
        
        # Проверяем результат
        cur.execute("SELECT * FROM user_filters WHERE telegram_id = ?", (telegram_id,))
        saved_record = cur.fetchone()
        if saved_record:
            print(f"DEBUG: Проверка после сохранения расстояния: {dict(saved_record)}")
        else:
            print("ERROR: Запись не найдена после сохранения расстояния!")
            conn.close()
            return False
        
        conn.close()
        print(f"DEBUG: Расстояние сохранено успешно для пользователя {telegram_id}")
        return True
        
    except Exception as e:
        print(f"ERROR: Критическая ошибка при сохранении расстояния: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_user_filters(telegram_id, target_filters: List[str], distance_km: int):
    """Сохраняет фильтры пользователя (полная версия для обратной совместимости)"""
    import json
    
    print(f"DEBUG: save_user_filters вызвана с параметрами:")
    print(f"  telegram_id: {telegram_id}")
    print(f"  target_filters: {target_filters}")
    print(f"  distance_km: {distance_km}")
    
    # Если передан None для distance_km, сохраняем как NULL
    distance_value = distance_km if distance_km is not None else None
    target_filters_json = json.dumps(target_filters, ensure_ascii=False) if target_filters else None
    
    print(f"DEBUG: Подготовленные данные для сохранения:")
    print(f"  target_filters_json: {target_filters_json}")
    print(f"  distance_value: {distance_value}")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Проверяем, существует ли таблица
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_filters'")
        table_exists = cur.fetchone()
        if not table_exists:
            print("ERROR: Таблица user_filters не существует!")
            conn.close()
            return
        
        # Проверяем, существует ли запись
        cur.execute("SELECT id FROM user_filters WHERE telegram_id = ?", (telegram_id,))
        existing = cur.fetchone()
        
        if existing:
            # Обновляем существующую запись
            print(f"DEBUG: Обновляем существующую запись (id: {existing['id']})")
            cur.execute("""
            UPDATE user_filters 
            SET target_filters = ?, distance_filter = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """, (target_filters_json, distance_value, telegram_id))
        else:
            # Создаем новую запись
            print("DEBUG: Создаем новую запись")
            cur.execute("""
            INSERT INTO user_filters (telegram_id, target_filters, distance_filter, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (telegram_id, target_filters_json, distance_value))
        
        # Проверяем количество затронутых строк
        rows_affected = cur.rowcount
        print(f"DEBUG: Количество затронутых строк: {rows_affected}")
        
        conn.commit()
        print("DEBUG: Транзакция зафиксирована")
        
        # Проверяем, что сохранилось
        cur.execute("SELECT * FROM user_filters WHERE telegram_id = ?", (telegram_id,))
        saved_filter = cur.fetchone()
        if saved_filter:
            print(f"DEBUG: Сохраненные фильтры: {dict(saved_filter)}")
        else:
            print("ERROR: Фильтры не найдены после сохранения!")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Ошибка при сохранении фильтров: {e}")
        import traceback
        traceback.print_exc()


def get_user_filters(telegram_id):
    """Получает фильтры пользователя"""
    import json
    
    print(f"DEBUG: get_user_filters вызвана для пользователя {telegram_id}")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Проверяем, существует ли таблица
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_filters'")
        table_exists = cur.fetchone()
        if not table_exists:
            print("ERROR: Таблица user_filters не существует!")
            conn.close()
            return None
        
        cur.execute("SELECT * FROM user_filters WHERE telegram_id = ?", (telegram_id,))
        filters = cur.fetchone()
        conn.close()
        
        print(f"DEBUG: Загруженные фильтры для пользователя {telegram_id}: {dict(filters) if filters else 'Нет данных'}")
        
        if filters:
            try:
                # Парсим JSON с фильтрами целей
                target_filters = []
                if filters['target_filters']:
                    target_filters = json.loads(filters['target_filters'])
                
                result = {
                    'target_filters': target_filters,
                    'distance_filter': filters['distance_filter']
                }
                print(f"DEBUG: Обработанные фильтры: {result}")
                return result
            except json.JSONDecodeError as e:
                print(f"ERROR: Ошибка парсинга JSON фильтров: {e}")
                return None
        
        return None
        
    except Exception as e:
        print(f"ERROR: Ошибка при получении фильтров: {e}")
        import traceback
        traceback.print_exc()
        return None


def debug_filters_table():
    """Отладочная функция для проверки таблицы фильтров"""
    print("DEBUG: Проверка таблицы user_filters")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Проверяем, существует ли таблица
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_filters'")
        table_exists = cur.fetchone()
        
        if not table_exists:
            print("ERROR: Таблица user_filters НЕ СУЩЕСТВУЕТ!")
            conn.close()
            return
        
        # Проверяем структуру таблицы
        cur.execute("PRAGMA table_info(user_filters)")
        columns = cur.fetchall()
        print("DEBUG: Структура таблицы user_filters:")
        for col in columns:
            print(f"  {dict(col)}")
        
        # Показываем все записи
        cur.execute("SELECT * FROM user_filters ORDER BY updated_at DESC")
        all_filters = cur.fetchall()
        print(f"DEBUG: Всего записей в user_filters: {len(all_filters)}")
        for i, f in enumerate(all_filters):
            print(f"  {i+1}. {dict(f)}")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Ошибка при отладке таблицы: {e}")
        import traceback
        traceback.print_exc()


# ========== Функции расчета расстояния ==========
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Вычисляет расстояние между двумя точками на Земле в километрах
    Использует формулу гаверсинуса
    """
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')  # Если координаты неизвестны, считаем расстояние бесконечным
    
    # Переводим градусы в радианы
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Формула гаверсинуса
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Радиус Земли в километрах
    r = 6371
    
    return c * r


# ========== Просмотр анкет с фильтрацией ==========
def get_filtered_profile(current_user_id, target_filters: List[str] = None, distance_km: int = None):
    """
    Возвращает случайную анкету с учетом фильтров пользователя
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Получаем данные текущего пользователя для расчета расстояния
    cur.execute("SELECT latitude, longitude FROM users WHERE telegram_id = ?", (current_user_id,))
    current_user_data = cur.fetchone()
    
    # Базовый запрос
    query = """
    SELECT * FROM users
    WHERE telegram_id != ?
      AND telegram_id NOT IN (
          SELECT to_user FROM likes
          WHERE from_user = ?
            AND created_at > datetime('now', '-9 days')
      )
    """
    params = [current_user_id, current_user_id]
    
    # Добавляем фильтр по целям
    if target_filters and len(target_filters) > 0:
        placeholders = ','.join(['?' for _ in target_filters])
        query += f" AND target IN ({placeholders})"
        params.extend(target_filters)
    
    query += " ORDER BY RANDOM()"
    
    cur.execute(query, params)
    profiles = cur.fetchall()
    
    # Фильтруем по расстоянию если указано
    if distance_km and current_user_data and current_user_data['latitude'] and current_user_data['longitude']:
        filtered_profiles = []
        for profile in profiles:
            if profile['latitude'] and profile['longitude']:
                distance = calculate_distance(
                    current_user_data['latitude'], current_user_data['longitude'],
                    profile['latitude'], profile['longitude']
                )
                if distance <= distance_km:
                    filtered_profiles.append(profile)
            # Если у профиля нет координат, не показываем при фильтре по расстоянию
        
        profiles = filtered_profiles
    
    conn.close()
    return profiles[0] if profiles else None


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