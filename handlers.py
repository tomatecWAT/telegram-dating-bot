from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import aiohttp

from database import (
    get_user_by_telegram_id,
    add_user,
    update_user_field,
    update_user_coordinates,
    get_next_profile_for,
    get_random_profile,
    get_filtered_profile,
    add_like,
    check_match,
    save_user_filters,
    save_user_target_filters,
    save_user_distance_filter,
    get_user_filters,
    debug_filters_table
)

from keyboards import (
    gender_keyboard,
    target_keyboard,
    location_keyboard,
    get_city_keyboard_with_previous,
    filter_type_keyboard,
    filter_targets_keyboard,
    distance_keyboard,
    filters_completed_keyboard,
    profile_menu,
    profile_menu_text,
    view_menu,
    view_menu_text,
    paused_menu,
    paused_menu_text,
    stopped_menu,
    stopped_menu_text
)

router = Router()

# in-memory map user_id -> last shown profile row
viewing_state = {}

# ========== FSM для регистрации ==========
class Registration(StatesGroup):
    gender = State()
    name = State()
    age = State()
    city_choice = State()  # новое состояние для выбора способа указания города
    city = State()
    target = State()
    bio = State()
    photo = State()

# ========== FSM для фильтров ==========
class FilterSettings(StatesGroup):
    filter_type_selection = State()  # выбор типа фильтра (цель/расстояние)
    target_selection = State()       # настройка целей
    distance_selection = State()     # настройка расстояния

# ========== Функция определения города по координатам ==========
async def get_city_from_coordinates(latitude, longitude):
    """
    Определение города по координатам через Nominatim API
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'accept-language': 'ru',  # Получаем ответ на русском
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'TelegramDatingBot/1.0'  # Обязательный заголовок для Nominatim
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Пытаемся извлечь город из ответа
                    address = data.get('address', {})
                    
                    # Ищем город в разных полях (в порядке приоритета)
                    city = (
                        address.get('city') or 
                        address.get('town') or 
                        address.get('village') or 
                        address.get('municipality') or
                        address.get('county') or
                        address.get('state')
                    )
                    
                    if city:
                        return city
                    else:
                        # Если не нашли город, возвращаем общую информацию
                        country = address.get('country', 'Неизвестная страна')
                        return f"Город рядом с {country}"
                else:
                    return f"Координаты {latitude:.2f}, {longitude:.2f}"
                    
    except Exception as e:
        # В случае ошибки возвращаем координаты
        return f"Координаты {latitude:.2f}, {longitude:.2f}"

# ========== Команды ==========

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user = get_user_by_telegram_id(message.from_user.id)
    if user:
        # Если анкета уже есть, показываем меню профиля
        await message.answer("С возвращением! 👋")
        await cmd_myprofile(message)
    else:
        # Если анкеты нет, начинаем регистрацию
        await message.answer("Привет! 👋 Давайте заполним вашу анкету.", reply_markup=ReplyKeyboardRemove())
        await message.answer("Выбери свой пол:", reply_markup=gender_keyboard)
        await state.set_state(Registration.gender)

@router.message(Command("myprofile"))
async def cmd_myprofile(message: Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("У тебя ещё нет анкеты. Используй /resetprofile для создания.")
        return

    # Отображение пола с эмодзи
    gender_display = "👩 Девушка" if user['gender'] == "female" else "👨 Парень"
    
    text = (
        f"👋 Имя: {user['name'] or 'Не указано'}\n"
        f"👤 Пол: {gender_display}\n"
        f"🎂 Возраст: {user['age']}\n"
        f"🏙️ Город: {user['city']}\n"
        f"🎯 Цель: {user['target']}\n"
        f"💬 О себе: {user['bio']}"
    )
    if user['photo']:
        await message.answer_photo(photo=user['photo'], caption=text)
    else:
        await message.answer(text)

    await message.answer(profile_menu_text, reply_markup=profile_menu)

@router.message(Command("editprofile"))
async def cmd_editprofile(message: Message, state: FSMContext):
    await message.answer("Редактируем анкету. Выбери свой пол:", reply_markup=ReplyKeyboardRemove())
    await message.answer("Нажми на кнопку:", reply_markup=gender_keyboard)
    await state.set_state(Registration.gender)
    # Сохраняем флаг, что это редактирование
    await state.update_data(is_editing=True)

@router.message(Command("resetprofile"))
async def cmd_resetprofile(message: Message, state: FSMContext):
    await message.answer("Заполним анкету заново! Выбери свой пол:", reply_markup=ReplyKeyboardRemove())
    await message.answer("Нажми на кнопку:", reply_markup=gender_keyboard)
    await state.set_state(Registration.gender)
    # Сохраняем флаг, что это сброс профиля
    await state.update_data(is_editing=True)

@router.message(F.text == "🔄 Заполнить анкету заново")
async def reset_profile_button(message: Message, state: FSMContext):
    await message.answer("Заполним анкету заново! Выбери свой пол:", reply_markup=ReplyKeyboardRemove())
    await message.answer("Нажми на кнопку:", reply_markup=gender_keyboard)
    await state.set_state(Registration.gender)
    # Сохраняем флаг, что это сброс профиля
    await state.update_data(is_editing=True)

# ========== Фильтры - НОВЫЙ ФЛОУ ==========
@router.message(F.text == "🔧 Настроить фильтры")
async def setup_filters(message: Message, state: FSMContext):
    # Получаем текущие фильтры пользователя
    current_filters = get_user_filters(message.from_user.id)
    
    if current_filters:
        targets = current_filters['target_filters']
        distance = current_filters['distance_filter']
        target_text = ', '.join(targets) if targets else "Все"
        distance_text = f"{distance} км" if distance else "Без ограничений"
        
        filter_status = (
            f"🔧 Текущие фильтры:\n\n"
            f"🎯 Цели знакомства: {target_text}\n"
            f"📍 Максимальное расстояние: {distance_text}\n\n"
            f"Выберите, какой фильтр хотите настроить:"
        )
    else:
        filter_status = (
            f"🔧 Настройка фильтров\n\n"
            f"🎯 Цели знакомства: Все\n"
            f"📍 Максимальное расстояние: Без ограничений\n\n"
            f"Выберите, какой фильтр хотите настроить:"
        )
    
    await message.answer(filter_status, reply_markup=filter_type_keyboard)
    await state.set_state(FilterSettings.filter_type_selection)

# ========== Выбор типа фильтра ==========
@router.message(FilterSettings.filter_type_selection, F.text == "🎯 Цель")
async def setup_target_filters(message: Message, state: FSMContext):
    # Получаем текущие цели
    current_filters = get_user_filters(message.from_user.id)
    current_targets = []
    if current_filters and current_filters['target_filters']:
        current_targets = current_filters['target_filters']
    
    if current_targets:
        targets_text = ', '.join(current_targets)
        instruction = f"🎯 Настройка целей знакомства\n\nТекущие цели: {targets_text}\n\nВыберите цели (можно несколько):"
    else:
        instruction = f"🎯 Настройка целей знакомства\n\nВыберите цели (можно несколько):"
    
    await message.answer(instruction, reply_markup=filter_targets_keyboard)
    await state.set_state(FilterSettings.target_selection)
    await state.update_data(selected_targets=current_targets.copy() if current_targets else [])

@router.message(FilterSettings.filter_type_selection, F.text == "📍 Расстояние")
async def setup_distance_filters(message: Message, state: FSMContext):
    # Получаем текущее расстояние
    current_filters = get_user_filters(message.from_user.id)
    current_distance = None
    if current_filters:
        current_distance = current_filters['distance_filter']
    
    if current_distance:
        distance_text = f"{current_distance} км"
        instruction = f"📍 Настройка максимального расстояния\n\nТекущее расстояние: {distance_text}\n\nВыберите новое расстояние:"
    else:
        instruction = f"📍 Настройка максимального расстояния\n\nВыберите максимальное расстояние:"
    
    await message.answer(instruction, reply_markup=distance_keyboard)
    await state.set_state(FilterSettings.distance_selection)

@router.message(FilterSettings.filter_type_selection, F.text == "👀 Посмотреть анкеты")
async def view_profiles_from_filters(message: Message, state: FSMContext):
    await state.clear()
    await cmd_view_filtered(message)

@router.message(FilterSettings.filter_type_selection, F.text == "📄 Моя анкета")
async def view_profile_from_filters(message: Message, state: FSMContext):
    await state.clear()
    await cmd_myprofile(message)

@router.message(Command("setup_filters"))
async def cmd_setup_filters(message: Message, state: FSMContext):
    """Команда для быстрого доступа к настройке фильтров"""
    await setup_filters(message, state)

# ========== Callback-хендлеры ==========

# Callback-хендлер для выбора пола
@router.callback_query(F.data.in_(["gender_female", "gender_male"]))
async def handle_gender_selection(callback: CallbackQuery, state: FSMContext):
    # Получаем выбранный пол из callback_data
    gender = "female" if callback.data == "gender_female" else "male"
    
    # Сохраняем в FSM
    await state.update_data(gender=gender)
    
    # Отвечаем на callback и редактируем сообщение
    gender_text = "👩 Девушка" if gender == "female" else "👨 Парень"
    await callback.message.edit_text(f"Выбран пол: {gender_text}")
    
    # Переходим к вводу имени
    await callback.message.answer("Как тебя зовут? Напиши своё имя:")
    await state.set_state(Registration.name)
    
    # Обязательно отвечаем на callback
    await callback.answer()

# ========== Настройка целей ==========
@router.callback_query(FilterSettings.target_selection, F.data.startswith("filter_target_"))
async def handle_target_filter_selection(callback: CallbackQuery, state: FSMContext):
    print(f"DEBUG: handle_target_filter_selection вызван с callback.data = '{callback.data}'")
    
    data = await state.get_data()
    selected_targets = data.get('selected_targets', [])
    print(f"DEBUG: Текущие выбранные цели: {selected_targets}")
    
    if callback.data == "filter_target_all":
        print("DEBUG: Выбраны ВСЕ цели")
        # Выбираем все цели
        selected_targets = ["Дружба", "Общение", "Отношения", "Ничего серьезного", "Свидания"]
        await state.update_data(selected_targets=selected_targets)
        
        await callback.message.edit_text(
            f"🎯 Настройка целей знакомства\n\n"
            f"✅ Выбраны все цели!\n"
            f"Выбранные цели: {', '.join(selected_targets)}",
            reply_markup=filter_targets_keyboard
        )
    elif callback.data == "filter_targets_save":
        print("DEBUG: Нажата кнопка СОХРАНИТЬ")
        # Сохраняем цели
        if not selected_targets:
            print("DEBUG: Цели не выбраны, используем все по умолчанию")
            selected_targets = ["Дружба", "Общение", "Отношения", "Ничего серьезного", "Свидания"]
        
        print(f"DEBUG: Сохраняем цели: {selected_targets}")
        success = save_user_target_filters(callback.from_user.id, selected_targets)
        
        if success:
            await callback.message.edit_text(
                f"✅ Цели сохранены!\n\n"
                f"Сохранённые цели: {', '.join(selected_targets)}\n\n"
                f"Выберите, что настроить дальше:",
            )
            
            # Возвращаемся к выбору типа фильтра
            await callback.message.answer(
                await get_current_filters_text(callback.from_user.id),
                reply_markup=filter_type_keyboard
            )
            await state.set_state(FilterSettings.filter_type_selection)
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при сохранении целей!\n"
                f"Попробуйте еще раз.",
                reply_markup=filter_targets_keyboard
            )
    else:
        print(f"DEBUG: Переключение конкретной цели: {callback.data}")
        # Переключаем выбор конкретной цели
        target = callback.data.replace("filter_target_", "")
        print(f"DEBUG: Извлеченная цель: '{target}'")
        
        if target in selected_targets:
            selected_targets.remove(target)
            print(f"DEBUG: Удалена цель '{target}'")
        else:
            selected_targets.append(target)
            print(f"DEBUG: Добавлена цель '{target}'")
        
        await state.update_data(selected_targets=selected_targets)
        
        target_text = ', '.join(selected_targets) if selected_targets else "Ничего не выбрано"
        await callback.message.edit_text(
            f"🎯 Настройка целей знакомства\n\n"
            f"Выбранные цели: {target_text}",
            reply_markup=filter_targets_keyboard
        )
    
    await callback.answer()

# ========== Настройка расстояния ==========
@router.callback_query(FilterSettings.distance_selection, F.data.startswith("filter_distance_"))
async def handle_distance_filter_selection(callback: CallbackQuery, state: FSMContext):
    print(f"DEBUG: handle_distance_filter_selection вызван с callback.data = '{callback.data}'")
    
    if callback.data == "filter_distance_unlimited":
        distance_km = None
        distance_text = "Без ограничений"
    else:
        distance_km = int(callback.data.replace("filter_distance_", ""))
        distance_text = f"до {distance_km} км"
    
    print(f"DEBUG: Сохраняем расстояние: {distance_km}")
    
    # Сохраняем расстояние
    success = save_user_distance_filter(callback.from_user.id, distance_km)
    
    if success:
        await callback.message.edit_text(
            f"✅ Расстояние сохранено!\n\n"
            f"Максимальное расстояние: {distance_text}\n\n"
            f"Выберите, что настроить дальше:"
        )
        
        # Возвращаемся к выбору типа фильтра
        await callback.message.answer(
            await get_current_filters_text(callback.from_user.id),
            reply_markup=filter_type_keyboard
        )
        await state.set_state(FilterSettings.filter_type_selection)
    else:
        await callback.message.edit_text(
            f"❌ Ошибка при сохранении расстояния!\n"
            f"Попробуйте еще раз.",
            reply_markup=distance_keyboard
        )
    
    await callback.answer()

# ========== Вспомогательная функция ==========
async def get_current_filters_text(telegram_id):
    """Возвращает текст с текущими фильтрами"""
    current_filters = get_user_filters(telegram_id)
    
    if current_filters:
        targets = current_filters['target_filters']
        distance = current_filters['distance_filter']
        target_text = ', '.join(targets) if targets else "Все"
        distance_text = f"{distance} км" if distance else "Без ограничений"
    else:
        target_text = "Все"
        distance_text = "Без ограничений"
    
    return (
        f"🔧 Текущие фильтры:\n\n"
        f"🎯 Цели знакомства: {target_text}\n"
        f"📍 Максимальное расстояние: {distance_text}\n\n"
        f"Выберите, какой фильтр хотите настроить:"
    )

# ========== Действия после завершения настройки фильтров ==========
@router.callback_query(F.data == "start_viewing_profiles")
async def start_viewing_profiles(callback: CallbackQuery):
    """Начинаем просмотр анкет после настройки фильтров"""
    await callback.message.delete()  # Удаляем сообщение с кнопками
    
    # Имитируем нажатие кнопки "Смотреть анкеты"
    mock_message = callback.message
    mock_message.from_user = callback.from_user
    
    await cmd_view_filtered(mock_message)
    await callback.answer()

@router.callback_query(F.data == "change_filters")
async def change_filters(callback: CallbackQuery, state: FSMContext):
    """Изменяем фильтры заново"""
    # Показываем меню выбора типа фильтра
    await callback.message.edit_text(
        await get_current_filters_text(callback.from_user.id),
        reply_markup=filter_type_keyboard
    )
    
    await state.set_state(FilterSettings.filter_type_selection)
    await callback.answer()

# ========== FSM-хендлеры регистрации ==========
@router.message(Registration.name)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(Registration.age)

@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    
    # Проверяем, редактируем ли мы профиль
    data = await state.get_data()
    is_editing = data.get('is_editing', False)
    previous_city = None
    
    if is_editing:
        # Получаем текущий город пользователя
        user = get_user_by_telegram_id(message.from_user.id)
        if user and user['city']:  # Используем dictionary-style access
            previous_city = user['city']
    
    # Создаем клавиатуру с учетом предыдущего города
    keyboard = get_city_keyboard_with_previous(previous_city)
    
    if previous_city and not previous_city.startswith("📍"):
        await message.answer(f"Укажи свой город. Можешь оставить текущий ({previous_city}) или написать новый:", reply_markup=keyboard)
    else:
        await message.answer("Укажи свой город или отправь геолокацию:", reply_markup=keyboard)
    
    await state.set_state(Registration.city_choice)

# Обработка выбора предыдущего города
@router.message(Registration.city_choice, F.text.startswith("🏙️ "))
async def reg_city_previous_choice(message: Message, state: FSMContext):
    # Извлекаем название города из текста кнопки
    city = message.text.replace("🏙️ ", "")
    await state.update_data(city=city)
    await message.answer(f"Отлично! Город остается: {city}", reply_markup=ReplyKeyboardRemove())
    await message.answer("Какая цель знакомства?", reply_markup=target_keyboard)
    await state.set_state(Registration.target)

# Обработка геолокации
@router.message(Registration.city_choice, F.location)
async def reg_city_location_choice(message: Message, state: FSMContext):
    # Получаем координаты
    latitude = message.location.latitude
    longitude = message.location.longitude
    
    # Определяем город по координатам
    city_name = await get_city_from_coordinates(latitude, longitude)
    
    # Сохраняем город и координаты
    await state.update_data(city=city_name, latitude=latitude, longitude=longitude)
    await message.answer(f"Отлично! Определен город: {city_name}", reply_markup=ReplyKeyboardRemove())
    await message.answer("Какая цель знакомства?", reply_markup=target_keyboard)
    await state.set_state(Registration.target)

# Обработка текстового ввода города
@router.message(Registration.city_choice)
async def reg_city_text_input(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer(f"Город сохранен: {message.text}", reply_markup=ReplyKeyboardRemove())
    await message.answer("Какая цель знакомства?", reply_markup=target_keyboard)
    await state.set_state(Registration.target)

@router.message(Registration.target)
async def reg_target(message: Message, state: FSMContext):
    # Список допустимых целей
    valid_targets = ["🤝 Дружба", "💬 Общение", "❤️ Отношения", "😌 Ничего серьезного", "🌟 Свидания"]
    
    if message.text in valid_targets:
        # Сохраняем цель без эмодзи для базы данных
        target_clean = message.text.split(" ", 1)[1]  # Убираем эмодзи в начале
        await state.update_data(target=target_clean)
        await message.answer(f"Цель знакомства: {message.text}", reply_markup=ReplyKeyboardRemove())
    else:
        # Если пользователь ввел что-то другое, сохраняем как есть
        await state.update_data(target=message.text)
        await message.answer(f"Цель знакомства: {message.text}", reply_markup=ReplyKeyboardRemove())
    
    await message.answer("Напиши пару слов о себе.")
    await state.set_state(Registration.bio)

@router.message(Registration.bio)
async def reg_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await message.answer("Теперь пришли фото для анкеты.")
    await state.set_state(Registration.photo)

@router.message(Registration.photo, F.photo)
async def reg_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.update_data(photo=photo_id)
    data = await state.get_data()

    # Сохраняем пользователя с новыми полями
    add_user(
        telegram_id=message.from_user.id,
        name=data["name"],
        gender=data["gender"],
        age=data["age"],
        city=data["city"],
        target=data["target"],
        bio=data["bio"],
        photo=data["photo"],
        latitude=data.get("latitude"),
        longitude=data.get("longitude")
    )

    await message.answer("Анкета сохранена! 🎉", reply_markup=profile_menu)
    await message.answer(profile_menu_text, reply_markup=profile_menu)
    await state.clear()

# ========== Просмотр анкет с фильтрацией ==========
@router.message(F.text == "👀 Смотреть анкеты")
async def cmd_view_filtered(message: Message):
    # Получаем фильтры пользователя
    filters = get_user_filters(message.from_user.id)
    print(f"DEBUG: Фильтры при просмотре анкет для пользователя {message.from_user.id}: {filters}")
    
    if filters:
        # Используем фильтрацию
        profile = get_filtered_profile(
            message.from_user.id,
            target_filters=filters['target_filters'] if filters['target_filters'] else None,
            distance_km=filters['distance_filter']
        )
        print(f"DEBUG: Используем фильтрацию. Найденный профиль: {profile['name'] if profile else 'Нет подходящих'}")
    else:
        # Используем стандартный просмотр без фильтров
        profile = get_random_profile(message.from_user.id)
        print(f"DEBUG: Без фильтров. Найденный профиль: {profile['name'] if profile else 'Нет анкет'}")
    
    if not profile:
        await message.answer(
            "❌ Нет анкет для просмотра!\n\n"
            "Возможные причины:\n"
            "• Фильтры слишком строгие\n"
            "• Все подходящие анкеты уже просмотрены\n\n"
            "Попробуй изменить фильтры.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔧 Настроить фильтры")]],
                resize_keyboard=True
            )
        )
        return

    # Отображение пола с эмодзи
    gender_display = "👩 Девушка" if profile['gender'] == "female" else "👨 Парень"
    
    # Показываем информацию о том, что фильтры работают
    filter_info = ""
    if filters:
        targets_text = ', '.join(filters['target_filters']) if filters['target_filters'] else "Все"
        distance_text = f"{filters['distance_filter']} км" if filters['distance_filter'] else "∞"
        filter_info = f"🔍 Фильтры: {targets_text} | {distance_text}\n\n"
    
    text = (
        f"{filter_info}"
        f"👋 Имя: {profile['name'] or 'Не указано'}\n"
        f"👤 Пол: {gender_display}\n"
        f"🎂 Возраст: {profile['age']}\n"
        f"🏙️ Город: {profile['city']}\n"
        f"🎯 Цель: {profile['target']}\n"
        f"💬 О себе: {profile['bio']}"
    )
    
    if profile['photo']:
        await message.answer_photo(photo=profile['photo'], caption=text)
    else:
        await message.answer(text)

    # remember which profile we've shown to this user so Like/Dislike applies to it
    viewing_state[message.from_user.id] = profile
    await message.answer(view_menu_text, reply_markup=view_menu)

@router.message(Command("view"))
async def cmd_view_command_filtered(message: Message):
    # Получаем фильтры пользователя
    filters = get_user_filters(message.from_user.id)
    
    if filters:
        # Используем фильтрацию
        profile = get_filtered_profile(
            message.from_user.id,
            target_filters=filters['target_filters'] if filters['target_filters'] else None,
            distance_km=filters['distance_filter']
        )
    else:
        # Используем стандартный просмотр без фильтров
        profile = get_random_profile(message.from_user.id)
    
    if not profile:
        await message.answer(
            "❌ Нет анкет для просмотра!\n\n"
            "Попробуй настроить фильтры.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔧 Настроить фильтры")]],
                resize_keyboard=True
            )
        )
        return

    # Отображение пола с эмодзи
    gender_display = "👩 Девушка" if profile['gender'] == "female" else "👨 Парень"
    
    # Показываем информацию о том, что фильтры работают
    filter_info = ""
    if filters:
        targets_text = ', '.join(filters['target_filters']) if filters['target_filters'] else "Все"
        distance_text = f"{filters['distance_filter']} км" if filters['distance_filter'] else "∞"
        filter_info = f"🔍 Фильтры: {targets_text} | {distance_text}\n\n"
    
    text = (
        f"{filter_info}"
        f"👋 Имя: {profile['name'] or 'Не указано'}\n"
        f"👤 Пол: {gender_display}\n"
        f"🎂 Возраст: {profile['age']}\n"
        f"🏙️ Город: {profile['city']}\n"
        f"🎯 Цель: {profile['target']}\n"
        f"💬 О себе: {profile['bio']}"
    )
    
    if profile['photo']:
        await message.answer_photo(photo=profile['photo'], caption=text)
    else:
        await message.answer(text)

    # remember which profile we've shown to this user so Like/Dislike applies to it
    viewing_state[message.from_user.id] = profile
    await message.answer(view_menu_text, reply_markup=view_menu)

# ========== Логика просмотра анкет (обновленная) ==========
@router.message(F.text == "❤️ Лайк")
async def like_profile(message: Message):
    target = viewing_state.get(message.from_user.id)
    if not target:
        await message.answer("Анкеты закончились.")
        return
    
    target_telegram_id = target['telegram_id']
    add_like(message.from_user.id, target_telegram_id, action="like")
    if check_match(message.from_user.id, target_telegram_id):
        await message.answer("🎉 У вас совпадение! Напишите друг другу в телеграм.")
    else:
        await message.answer("Лайк поставлен ✅")

    # clear viewed profile so next view will fetch another
    viewing_state.pop(message.from_user.id, None)
    await cmd_view_filtered(message)

@router.message(F.text == "👎 Дизлайк")
async def dislike_profile(message: Message):
    target = viewing_state.get(message.from_user.id)
    if target:
        target_telegram_id = target['telegram_id']
        add_like(message.from_user.id, target_telegram_id, action="dislike")
        viewing_state.pop(message.from_user.id, None)
    await message.answer("Пропускаем эту анкету 👌")
    await cmd_view_filtered(message)

@router.message(F.text == "⏸ Приостановить поиск")
async def pause_search(message: Message):
    await message.answer(paused_menu_text, reply_markup=paused_menu)

@router.message(F.text == "🚫 Я больше не хочу никого искать")
async def stop_search(message: Message):
    await message.answer(stopped_menu_text, reply_markup=stopped_menu)

# ========== Отладочные команды ==========
@router.message(Command("debug_filters"))
async def debug_filters_command(message: Message):
    """Отладочная команда для проверки фильтров"""
    print("=== DEBUG FILTERS ===")
    debug_filters_table()
    
    user_filters = get_user_filters(message.from_user.id)
    await message.answer(
        f"🔧 Отладка фильтров:\n"
        f"Твои фильтры: {user_filters}\n"
        f"Подробности в консоли сервера."
    )

@router.message(Command("create_filters_table"))
async def create_filters_table_command(message: Message):
    """Принудительно создает таблицу фильтров"""
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        # Создаем таблицу фильтров
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            target_filters TEXT,
            distance_filter INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        
        # Проверяем создание
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_filters'")
        table_exists = cur.fetchone()
        
        if table_exists:
            await message.answer("✅ Таблица user_filters создана успешно!")
        else:
            await message.answer("❌ Не удалось создать таблицу user_filters")
        
        conn.close()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании таблицы: {e}")

@router.message(Command("test_filter_save"))
async def test_filter_save_command(message: Message):
    """Тестовая команда для проверки сохранения фильтров"""
    test_targets = ["Отношения", "Дружба"]
    test_distance = 15
    
    print("=== ТЕСТ СОХРАНЕНИЯ ФИЛЬТРОВ ===")
    
    # Тест сохранения целей
    success1 = save_user_target_filters(message.from_user.id, test_targets)
    print(f"Результат сохранения целей: {success1}")
    
    # Тест сохранения расстояния
    success2 = save_user_distance_filter(message.from_user.id, test_distance)
    print(f"Результат сохранения расстояния: {success2}")
    
    # Проверяем загрузку
    loaded_filters = get_user_filters(message.from_user.id)
    print(f"Загруженные фильтры: {loaded_filters}")
    
    await message.answer(
        f"🧪 Тест сохранения фильтров:\n"
        f"Цели: {success1} ✅ если True\n"
        f"Расстояние: {success2} ✅ если True\n"
        f"Загруженные: {loaded_filters}\n"
        f"Подробности в консоли."
    )

@router.message(Command("test_callbacks"))
async def test_callbacks_command(message: Message, state: FSMContext):
    """Тестовая команда для проверки callback'ов"""
    # Устанавливаем состояние для тестирования
    await state.set_state(FilterSettings.target_selection)
    await state.update_data(selected_targets=["Отношения"])
    
    await message.answer(
        "🧪 Тест callback'ов фильтров\n"
        "Попробуй нажать кнопки:",
        reply_markup=filter_targets_keyboard
    )