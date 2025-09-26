"""
Скрипт для диагностики проблем с базой данных и фильтрами
"""
import sqlite3
import json
from database import get_connection, save_user_filters, get_user_filters
from config import DB_PATH

def check_database_structure():
    """Проверяет структуру базы данных"""
    print("=== ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ ===")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Проверяем, существует ли таблица user_filters
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_filters'")
    table_exists = cur.fetchone()
    
    if table_exists:
        print("✅ Таблица user_filters существует")
        
        # Показываем структуру таблицы
        cur.execute("PRAGMA table_info(user_filters)")
        columns = cur.fetchall()
        print("📋 Структура таблицы user_filters:")
        for col in columns:
            print(f"   {col['name']} - {col['type']} {'(NOT NULL)' if col['notnull'] else '(NULL OK)'}")
    else:
        print("❌ Таблица user_filters НЕ существует!")
        return False
    
    conn.close()
    return True

def check_permissions():
    """Проверяет права доступа к базе данных"""
    print("\n=== ПРОВЕРКА ПРАВ ДОСТУПА ===")
    
    try:
        # Пробуем создать тестовую запись
        conn = get_connection()
        cur = conn.cursor()
        
        # Тестовая вставка
        cur.execute("INSERT INTO user_filters (telegram_id, target_filters, distance_filter) VALUES (?, ?, ?)", 
                   (999999, '["test"]', 10))
        conn.commit()
        print("✅ Запись в базу данных: УСПЕШНО")
        
        # Тестовое чтение
        cur.execute("SELECT * FROM user_filters WHERE telegram_id = ?", (999999,))
        result = cur.fetchone()
        if result:
            print("✅ Чтение из базы данных: УСПЕШНО")
            print(f"   Данные: {dict(result)}")
        else:
            print("❌ Чтение из базы данных: ПРОВАЛ")
        
        # Удаляем тестовую запись
        cur.execute("DELETE FROM user_filters WHERE telegram_id = ?", (999999,))
        conn.commit()
        print("✅ Удаление тестовой записи: УСПЕШНО")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка доступа к базе данных: {e}")
        return False

def manual_filter_test():
    """Тестирует сохранение фильтров вручную"""
    print("\n=== РУЧНОЕ ТЕСТИРОВАНИЕ ФИЛЬТРОВ ===")
    
    test_user_id = 779616206
    test_targets = ["Отношения", "Дружба"]
    test_distance = 15
    
    print(f"🧪 Тестируем с пользователем ID: {test_user_id}")
    print(f"   Цели: {test_targets}")
    print(f"   Расстояние: {test_distance} км")
    
    try:
        # Сохраняем фильтры
        print("\n1️⃣ Сохраняем фильтры...")
        save_user_filters(test_user_id, test_targets, test_distance)
        
        # Загружаем фильтры
        print("\n2️⃣ Загружаем фильтры...")
        loaded_filters = get_user_filters(test_user_id)
        
        if loaded_filters:
            print("✅ Фильтры загружены успешно!")
            print(f"   Загруженные данные: {loaded_filters}")
            
            # Проверяем корректность данных
            if (loaded_filters['target_filters'] == test_targets and 
                loaded_filters['distance_filter'] == test_distance):
                print("✅ Данные полностью корректны!")
                return True
            else:
                print("❌ Данные не совпадают с ожидаемыми!")
                return False
        else:
            print("❌ Фильтры не загрузились!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def check_all_filters():
    """Показывает все фильтры в базе данных"""
    print("\n=== ВСЕ ФИЛЬТРЫ В БАЗЕ ДАННЫХ ===")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM user_filters ORDER BY updated_at DESC")
        all_filters = cur.fetchall()
        
        if all_filters:
            print(f"📊 Найдено записей: {len(all_filters)}")
            for i, f in enumerate(all_filters, 1):
                print(f"\n{i}. Пользователь: {f['telegram_id']}")
                print(f"   Цели: {f['target_filters']}")
                print(f"   Расстояние: {f['distance_filter']} км")
                print(f"   Обновлено: {f['updated_at']}")
        else:
            print("📭 Фильтров в базе данных НЕТ")
            
    except Exception as e:
        print(f"❌ Ошибка при чтении фильтров: {e}")
    
    conn.close()

def recreate_filters_table():
    """Пересоздает таблицу фильтров"""
    print("\n=== ПЕРЕСОЗДАНИЕ ТАБЛИЦЫ ФИЛЬТРОВ ===")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Удаляем старую таблицу
        cur.execute("DROP TABLE IF EXISTS user_filters")
        print("🗑️ Старая таблица удалена")
        
        # Создаем новую таблицу
        cur.execute("""
        CREATE TABLE user_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            target_filters TEXT,
            distance_filter INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        print("✅ Новая таблица создана")
        
        # Проверяем создание
        cur.execute("PRAGMA table_info(user_filters)")
        columns = cur.fetchall()
        print("📋 Структура новой таблицы:")
        for col in columns:
            print(f"   {dict(col)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при пересоздании таблицы: {e}")
        return False
    finally:
        conn.close()

def main():
    """Основная диагностическая функция"""
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМ С ФИЛЬТРАМИ")
    print("=" * 50)
    
    # 1. Проверяем структуру базы данных
    if not check_database_structure():
        print("\n🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Таблица фильтров отсутствует!")
        print("Хотите пересоздать таблицу? (y/N): ", end="")
        if input().lower() in ['y', 'yes', 'д', 'да']:
            if recreate_filters_table():
                print("✅ Таблица пересоздана, попробуйте снова")
            else:
                print("❌ Не удалось пересоздать таблицу")
            return
        else:
            print("❌ Без таблицы фильтры работать не будут")
            return
    
    # 2. Проверяем права доступа
    if not check_permissions():
        print("\n🚨 ПРОБЛЕМА: Нет прав на запись в базу данных!")
        print("Проверьте права доступа к файлу:", DB_PATH)
        return
    
    # 3. Показываем текущие фильтры
    check_all_filters()
    
    # 4. Тестируем сохранение/загрузку
    if manual_filter_test():
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("Фильтры должны работать корректно.")
    else:
        print("\n🚨 ТЕСТЫ ПРОВАЛИЛИСЬ!")
        print("Фильтры не работают. Проверьте код или пересоздайте таблицу.")

if __name__ == "__main__":
    main()