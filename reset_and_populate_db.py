"""
Скрипт для полного сброса базы данных и добавления тестовых пользователей
ВНИМАНИЕ: Этот скрипт удалит ВСЕ данные из базы!
"""
import os
import sqlite3
from database import init_db, add_user, get_user_by_telegram_id
from config import DB_PATH


def reset_database():
    """Удаляет базу данных полностью"""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✅ База данных {DB_PATH} удалена")
    else:
        print(f"ℹ️ База данных {DB_PATH} не найдена")


def create_fresh_database():
    """Создает новую базу данных со всеми таблицами"""
    init_db()
    print("✅ Новая база данных создана со всеми таблицами")


def add_test_users():
    """Добавляет тестовых пользователей для проверки функционала"""
    
    # Тестовые пользователи с разными характеристиками
    test_users = [
        {
            'telegram_id': 1001,
            'name': 'Алексей',
            'gender': 'male',
            'age': 25,
            'city': 'Москва',
            'latitude': 55.7558,
            'longitude': 37.6173,
            'target': 'Отношения',
            'bio': 'Люблю путешествовать и читать книги. Ищу серьезные отношения.',
            'photo': None
        },
        {
            'telegram_id': 1002,
            'name': 'Мария',
            'gender': 'female',
            'age': 23,
            'city': 'Москва',
            'latitude': 55.7512,
            'longitude': 37.6180,
            'target': 'Общение',
            'bio': 'Художница, люблю современное искусство. Хочу найти интересных людей для общения.',
            'photo': None
        },
        {
            'telegram_id': 1003,
            'name': 'Дмитрий',
            'gender': 'male',
            'age': 30,
            'city': 'Санкт-Петербург',
            'latitude': 59.9311,
            'longitude': 30.3609,
            'target': 'Дружба',
            'bio': 'Программист, увлекаюсь технологиями. Ищу друзей по интересам.',
            'photo': None
        },
        {
            'telegram_id': 1004,
            'name': 'Елена',
            'gender': 'female',
            'age': 27,
            'city': 'Санкт-Петербург',
            'latitude': 59.9342,
            'longitude': 30.3351,
            'target': 'Свидания',
            'bio': 'Фотограф, обожаю природу и активный отдых. Открыта для новых знакомств.',
            'photo': None
        },
        {
            'telegram_id': 1005,
            'name': 'Андрей',
            'gender': 'male',
            'age': 28,
            'city': 'Казань',
            'latitude': 55.8304,
            'longitude': 49.0661,
            'target': 'Ничего серьезного',
            'bio': 'Музыкант, играю на гитаре. Хочу просто хорошо проводить время.',
            'photo': None
        },
        {
            'telegram_id': 1006,
            'name': 'Анна',
            'gender': 'female',
            'age': 24,
            'city': 'Екатеринбург',
            'latitude': 56.8431,
            'longitude': 60.6454,
            'target': 'Отношения',
            'bio': 'Врач, люблю помогать людям. Ищу надежного партнера для серьезных отношений.',
            'photo': None
        },
        {
            'telegram_id': 1007,
            'name': 'Максим',
            'gender': 'male',
            'age': 26,
            'city': 'Новосибирск',
            'latitude': 55.0084,
            'longitude': 82.9357,
            'target': 'Общение',
            'bio': 'Учитель истории, обожаю путешествия и изучение культур. Хочу найти единомышленников.',
            'photo': None
        },
        {
            'telegram_id': 1008,
            'name': 'София',
            'gender': 'female',
            'age': 22,
            'city': 'Краснодар',
            'latitude': 45.0355,
            'longitude': 38.9753,
            'target': 'Дружба',
            'bio': 'Студентка журфака, люблю писать статьи. Ищу друзей для интересного общения.',
            'photo': None
        },
        {
            'telegram_id': 1009,
            'name': 'Игорь',
            'gender': 'male',
            'age': 32,
            'city': 'Ростов-на-Дону',
            'latitude': 47.2357,
            'longitude': 39.7015,
            'target': 'Свидания',
            'bio': 'Повар, готовлю невероятные блюда. Хочу найти кого-то особенного для романтических свиданий.',
            'photo': None
        },
        {
            'telegram_id': 1010,
            'name': 'Виктория',
            'gender': 'female',
            'age': 29,
            'city': 'Воронеж',
            'latitude': 51.6720,
            'longitude': 39.1843,
            'target': 'Ничего серьезного',
            'bio': 'Дизайнер интерьеров, творческая натура. Просто хочу весело проводить время.',
            'photo': None
        }
    ]
    
    print("Добавляю тестовых пользователей...")
    
    for user_data in test_users:
        try:
            add_user(
                telegram_id=user_data['telegram_id'],
                name=user_data['name'],
                gender=user_data['gender'],
                age=user_data['age'],
                city=user_data['city'],
                target=user_data['target'],
                bio=user_data['bio'],
                photo=user_data['photo'],
                latitude=user_data['latitude'],
                longitude=user_data['longitude']
            )
            print(f"✅ Добавлен пользователь: {user_data['name']} ({user_data['city']})")
        except Exception as e:
            print(f"❌ Ошибка при добавлении пользователя {user_data['name']}: {e}")
    
    print(f"\n🎉 Добавлено {len(test_users)} тестовых пользователей")


def verify_users():
    """Проверяет, что пользователи успешно добавлены"""
    print("\n📊 Проверка добавленных пользователей:")
    
    test_ids = [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010]
    
    for user_id in test_ids:
        user = get_user_by_telegram_id(user_id)
        if user:
            print(f"✅ ID {user_id}: {user['name']} - {user['gender']} - {user['city']}")
        else:
            print(f"❌ Пользователь с ID {user_id} не найден")


def show_database_stats():
    """Показывает статистику базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Подсчет пользователей
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    
    # Подсчет по полу
    cur.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender")
    gender_stats = cur.fetchall()
    
    # Подсчет по городам
    cur.execute("SELECT city, COUNT(*) FROM users GROUP BY city ORDER BY COUNT(*) DESC")
    city_stats = cur.fetchall()
    
    # Подсчет по целям
    cur.execute("SELECT target, COUNT(*) FROM users GROUP BY target ORDER BY COUNT(*) DESC")
    target_stats = cur.fetchall()
    
    conn.close()
    
    print(f"\n📈 Статистика базы данных:")
    print(f"👥 Всего пользователей: {user_count}")
    
    print(f"\n👤 По полу:")
    for gender, count in gender_stats:
        gender_name = "Девушки" if gender == "female" else "Парни"
        print(f"  {gender_name}: {count}")
    
    print(f"\n🏙️ По городам:")
    for city, count in city_stats:
        print(f"  {city}: {count}")
    
    print(f"\n🎯 По целям:")
    for target, count in target_stats:
        print(f"  {target}: {count}")


def main():
    """Основная функция"""
    print("🚨 ВНИМАНИЕ! Этот скрипт полностью удалит текущую базу данных!")
    print("Вы уверены, что хотите продолжить? (y/N): ", end="")
    
    confirmation = input().strip().lower()
    
    if confirmation not in ['y', 'yes', 'д', 'да']:
        print("❌ Операция отменена")
        return
    
    print("\n🔄 Начинаю сброс базы данных...")
    
    # 1. Удаляем старую базу
    reset_database()
    
    # 2. Создаем новую базу
    create_fresh_database()
    
    # 3. Добавляем тестовых пользователей
    add_test_users()
    
    # 4. Проверяем результат
    verify_users()
    
    # 5. Показываем статистику
    show_database_stats()
    
    print("\n🎉 База данных успешно сброшена и заполнена тестовыми данными!")
    print("Теперь можно тестировать бота с реальными анкетами.")


if __name__ == "__main__":
    main()