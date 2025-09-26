from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ========== Инлайн-клавиатура для выбора пола ==========
gender_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="👩 Девушка", callback_data="gender_female"),
            InlineKeyboardButton(text="👨 Парень", callback_data="gender_male")
        ]
    ]
)

# ========== Клавиатура для выбора цели знакомства ==========
target_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤝 Дружба"), KeyboardButton(text="💬 Общение")],
        [KeyboardButton(text="❤️ Отношения"), KeyboardButton(text="😌 Ничего серьезного")],
        [KeyboardButton(text="🌟 Свидания")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ========== Клавиатура для отправки геолокации ==========
location_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Отправить мои координаты", request_location=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

def get_city_keyboard_with_previous(previous_city=None):
    """Создает клавиатуру с кнопкой предыдущего города (если есть) и кнопкой геолокации"""
    if previous_city and not previous_city.startswith("📍"):  # Проверяем, что это не координаты
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=f"🏙️ {previous_city}")],
                [KeyboardButton(text="📍 Отправить мои координаты", request_location=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    else:
        return location_keyboard

# ========== Клавиатуры для фильтров ==========
# Клавиатура для выбора целей (множественный выбор) - ЭТАП 1
filter_targets_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🤝 Дружба", callback_data="filter_target_Дружба"),
            InlineKeyboardButton(text="💬 Общение", callback_data="filter_target_Общение")
        ],
        [
            InlineKeyboardButton(text="❤️ Отношения", callback_data="filter_target_Отношения"),
            InlineKeyboardButton(text="😌 Ничего серьезного", callback_data="filter_target_Ничего серьезного")
        ],
        [InlineKeyboardButton(text="🌟 Свидания", callback_data="filter_target_Свидания")],
        [InlineKeyboardButton(text="✅ Все цели", callback_data="filter_target_all")],
        [InlineKeyboardButton(text="➡️ ДАЛЕЕ: Выбрать расстояние", callback_data="filter_targets_next")]
    ]
)

# Клавиатура для выбора расстояния - ЭТАП 2
distance_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Рядом (до 5 км)", callback_data="filter_distance_5")],
        [InlineKeyboardButton(text="🏘️ Соседи (до 10 км)", callback_data="filter_distance_10")],
        [InlineKeyboardButton(text="🌆 Неподалёку (до 30 км)", callback_data="filter_distance_30")],
        [InlineKeyboardButton(text="🌄 На горизонте (до 50 км)", callback_data="filter_distance_50")],
        [InlineKeyboardButton(text="🌍 Без ограничений", callback_data="filter_distance_unlimited")]
    ]
)

# Клавиатура после завершения настройки фильтров
filters_completed_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👀 Посмотреть анкеты", callback_data="start_viewing_profiles")],
        [InlineKeyboardButton(text="🔧 Изменить фильтры", callback_data="change_filters")]
    ]
)

# ========== Контекстные меню ==========
# Меню при просмотре моего профиля
profile_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👀 Смотреть анкеты")],
        [KeyboardButton(text="🔧 Настроить фильтры")],
        [KeyboardButton(text="🔄 Заполнить анкету заново")],
        [KeyboardButton(text="🖼️ Изменить фото анкеты")],
        [KeyboardButton(text="💬 Изменить текст анкеты (био)")],
        [KeyboardButton(text="🎯 Изменить цель")],
        [KeyboardButton(text="🎂 Изменить возраст")]
    ],
    resize_keyboard=True
)

profile_menu_text = (
    "📄 Меню профиля:\n"
    "1. Смотреть анкеты\n"
    "2. Настроить фильтры\n"
    "3. Заполнить анкету заново\n"
    "4. Изменить фото анкеты\n"
    "5. Изменить текст анкеты (био)\n"
    "6. Изменить цель\n"
    "7. Изменить возраст"
)

# Меню при просмотре чужой анкеты
view_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❤️ Лайк"), KeyboardButton(text="👎 Дизлайк")],
        [KeyboardButton(text="⏸ Приостановить поиск")]
    ],
    resize_keyboard=True
)

view_menu_text = (
    "👤 Меню просмотра анкеты:\n"
    "1. Лайк ❤️\n"
    "2. Дизлайк 👎\n"
    "3. Приостановить поиск ⏸"
)

# Меню при приостановленном поиске
paused_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👀 Смотреть анкеты")],
        [KeyboardButton(text="📄 Моя анкета")],
        [KeyboardButton(text="🚫 Я больше не хочу никого искать")]
    ],
    resize_keyboard=True
)

paused_menu_text = (
    "⏸ Поиск приостановлен. Доступные действия:\n"
    "1. Смотреть анкеты\n"
    "2. Моя анкета\n"
    "3. Я больше не хочу никого искать"
)

# Меню при остановленном поиске
stopped_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👀 Смотреть анкеты")]
    ],
    resize_keyboard=True
)

stopped_menu_text = (
    "🚫 Поиск остановлен. Доступные действия:\n"
    "1. Смотреть анкеты"
)