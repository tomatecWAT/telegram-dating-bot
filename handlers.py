from aiogram import Router, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from database import (
    get_user_by_telegram_id,
    add_user,
    update_user_field,
    get_next_profile_for,
    get_random_profile,
    add_like,
    check_match
)

router = Router()

# in-memory map user_id -> last shown profile row
viewing_state = {}

# ========== FSM для регистрации ==========
class Registration(StatesGroup):
    gender = State()
    age = State()
    city = State()
    target = State()
    bio = State()
    photo = State()

# ========== Контекстные меню ==========

# 2.1 Меню при просмотре моего профиля
profile_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👀 Смотреть анкеты")],
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
    "2. Изменить фото анкеты\n"
    "3. Изменить текст анкеты (био)\n"
    "4. Изменить цель\n"
    "5. Изменить возраст"
)

# 2.2 Меню при просмотре чужой анкеты
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

# 2.3 Меню при приостановленном поиске
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

# 2.4 Меню при остановленном поиске
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

# ========== Команды ==========

@router.message(Command("myprofile"))
async def cmd_myprofile(message: Message):
    user = get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("У тебя ещё нет анкеты. Используй /resetprofile для создания.")
        return

    text = (
        f"👤 Пол: {user[2]}\n"
        f"🎂 Возраст: {user[3]}\n"
        f"🏙️ Город: {user[4]}\n"
        f"🎯 Цель: {user[5]}\n"
        f"💬 О себе: {user[6]}"
    )
    if user[7]:
        await message.answer_photo(photo=user[7], caption=text)
    else:
        await message.answer(text)

    await message.answer(profile_menu_text, reply_markup=profile_menu)

@router.message(Command("editprofile"))
async def cmd_editprofile(message: Message, state: FSMContext):
    await message.answer("Редактируем анкету. Напиши свой пол (male/female/other):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.gender)

@router.message(Command("resetprofile"))
async def cmd_resetprofile(message: Message, state: FSMContext):
    await message.answer("Заполним анкету заново! Напиши свой пол (male/female/other):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.gender)

@router.message(F.text == "👀 Смотреть анкеты")
async def cmd_view(message: Message):
    profile = get_random_profile(message.from_user.id)
    if not profile:
        await message.answer("Пока нет анкет для просмотра.")
        return

    text = (
        f"👤 Пол: {profile[2]}\n"
        f"🎂 Возраст: {profile[3]}\n"
        f"🏙️ Город: {profile[4]}\n"
        f"🎯 Цель: {profile[5]}\n"
        f"💬 О себе: {profile[6]}"
    )
    if profile[7]:
        await message.answer_photo(photo=profile[7], caption=text)
    else:
        await message.answer(text)

    # remember which profile we've shown to this user so Like/Dislike applies to it
    viewing_state[message.from_user.id] = profile
    await message.answer(view_menu_text, reply_markup=view_menu)


@router.message(Command("view"))
async def cmd_view(message: Message):
    profile = get_random_profile(message.from_user.id)
    if not profile:
        await message.answer("Пока нет анкет для просмотра.")
        return

    text = (
        f"👤 Пол: {profile[2]}\n"
        f"🎂 Возраст: {profile[3]}\n"
        f"🏙️ Город: {profile[4]}\n"
        f"🎯 Цель: {profile[5]}\n"
        f"💬 О себе: {profile[6]}"
    )
    if profile[7]:
        await message.answer_photo(photo=profile[7], caption=text)
    else:
        await message.answer(text)

    # remember which profile we've shown to this user so Like/Dislike applies to it
    viewing_state[message.from_user.id] = profile
    await message.answer(view_menu_text, reply_markup=view_menu)

# ========== Логика просмотра анкет ==========

@router.message(F.text == "❤️ Лайк")
async def like_profile(message: Message):
    target = viewing_state.get(message.from_user.id)
    if not target:
        await message.answer("Анкеты закончились.")
        return
    # target is a row from users: (id, telegram_id, gender, age, city, target, bio, photo)
    target_telegram_id = target[1]
    add_like(message.from_user.id, target_telegram_id, action="like")
    if check_match(message.from_user.id, target_telegram_id):
        await message.answer("🎉 У вас совпадение! Напишите друг другу в телеграм.")
    else:
        await message.answer("Лайк поставлен ✅")

    # clear viewed profile so next view will fetch another
    viewing_state.pop(message.from_user.id, None)
    await cmd_view(message)


@router.message(F.text == "👎 Дизлайк")
async def dislike_profile(message: Message):
    target = viewing_state.get(message.from_user.id)
    if target:
        target_telegram_id = target[1]
        add_like(message.from_user.id, target_telegram_id, action="dislike")
        viewing_state.pop(message.from_user.id, None)
    await message.answer("Пропускаем эту анкету 👌")
    await cmd_view(message)
    # логика дизлайка — можно записать в отдельную таблицу

@router.message(F.text == "⏸ Приостановить поиск")
async def pause_search(message: Message):
    await message.answer(paused_menu_text, reply_markup=paused_menu)

@router.message(F.text == "🚫 Я больше не хочу никого искать")
async def stop_search(message: Message):
    await message.answer(stopped_menu_text, reply_markup=stopped_menu)

# ========== FSM-хендлеры регистрации ==========
@router.message(Registration.gender)
async def reg_gender(message: Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(Registration.age)

@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("В каком городе живёшь?")
    await state.set_state(Registration.city)

@router.message(Registration.city)
async def reg_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Какая цель знакомства?")
    await state.set_state(Registration.target)

@router.message(Registration.target)
async def reg_target(message: Message, state: FSMContext):
    await state.update_data(target=message.text)
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

    add_user(
        telegram_id=message.from_user.id,
        gender=data["gender"],
        age=data["age"],
        city=data["city"],
        target=data["target"],
        bio=data["bio"],
        photo=data["photo"]
    )

    await message.answer("Анкета сохранена! 🎉", reply_markup=profile_menu)
    await message.answer(profile_menu_text, reply_markup=profile_menu)
    await state.clear()




