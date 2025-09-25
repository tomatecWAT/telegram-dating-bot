# handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import (
    upsert_user_from_telegram,
    get_user_by_telegram_id,
    get_next_profile_for,
    add_like,
    check_and_create_match_if_any,
    get_user_by_id,
    get_profile_payload
)

router = Router()

# --- FSM States for registration ---
class RegStates(StatesGroup):
    waiting_gender = State()
    waiting_age = State()
    waiting_city = State()
    waiting_target = State()
    waiting_bio = State()
    waiting_photo = State()

# /start - начало регистрации (если профиль существует, кратко приветствуем)
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    existing = get_user_by_telegram_id(tg_id)
    if existing:
        await message.answer("С возвращением! Ваша анкета уже есть в базе. Используйте /browse чтобы смотреть других.")
        await state.clear()
        return

    await message.answer("Привет! Давай создадим твою анкету.\nСначала: укажи пол (male/female/other).")
    await state.set_state(RegStates.waiting_gender)

@router.message(RegStates.waiting_gender)
async def process_gender(message: Message, state: FSMContext):
    gender = message.text.strip().lower()
    if gender not in ("male", "female", "other"):
        await message.answer("Непонятно. Введи 'male', 'female' или 'other'.")
        return
    await state.update_data(gender=gender)
    await message.answer("Отлично. Укажи возраст (числом).")
    await state.set_state(RegStates.waiting_age)

@router.message(RegStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if age <= 0 or age > 120:
            raise ValueError
    except ValueError:
        await message.answer("Возраст должен быть корректным числом, например: 25")
        return
    await state.update_data(age=age)
    await message.answer("Укажи город.")
    await state.set_state(RegStates.waiting_city)

@router.message(RegStates.waiting_city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(city=city)
    await message.answer("Какая цель знакомства? (общение/дружба/отношения/другое)")
    await state.set_state(RegStates.waiting_target)

@router.message(RegStates.waiting_target)
async def process_target(message: Message, state: FSMContext):
    target = message.text.strip()
    await state.update_data(target=target)
    await message.answer("Напиши короткое описание о себе (bio).")
    await state.set_state(RegStates.waiting_bio)

@router.message(RegStates.waiting_bio)
async def process_bio(message: Message, state: FSMContext):
    bio = message.text.strip()
    await state.update_data(bio=bio)
    await message.answer("Пришли своё фото (как фото, не файл).")
    await state.set_state(RegStates.waiting_photo)

@router.message(RegStates.waiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1].file_id  # самый большой
    data = await state.get_data()
    tg_id = message.from_user.id

    # сохраняем или обновляем запись
    user_db_id = upsert_user_from_telegram(
        telegram_id=tg_id,
        gender=data.get("gender"),
        age=data.get("age"),
        city=data.get("city"),
        target=data.get("target"),
        bio=data.get("bio"),
        photo=photo
    )
    await message.answer("Анкета сохранена! Теперь можно смотреть профили: /browse")
    await state.clear()

@router.message(RegStates.waiting_photo)
async def process_photo_invalid(message: Message):
    await message.answer("Пожалуйста, пришли фото (как изображение).")

# /browse - показать одну карточку
@router.message(Command("browse"))
async def cmd_browse(message: Message):
    tg_id = message.from_user.id
    me = get_user_by_telegram_id(tg_id)
    if not me:
        await message.answer("Сначала зарегистрируйся: /start")
        return
    me_id = me["id"]
    candidate = get_next_profile_for(me_id)
    if not candidate:
        await message.answer("Пока нет доступных анкет. Попробуй позже.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Лайк", callback_data=f"like:{candidate['id']}"),
            InlineKeyboardButton(text="➡️ Пропуск", callback_data=f"skip:{candidate['id']}")
        ]
    ])

    text = (f"{candidate['gender'].title()}, {candidate['age']} лет\n"
            f"{candidate['city']}\nЦель: {candidate['target']}\n\n{candidate['bio']}")
    if candidate["photo"]:
        await message.answer_photo(photo=candidate["photo"], caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

# Колбэки like / skip
@router.callback_query(lambda c: c.data and c.data.startswith("like:"))
async def callback_like(query: CallbackQuery):
    data = query.data.split(":")
    to_user_id = int(data[1])
    from_tg_id = query.from_user.id
    from_row = get_user_by_telegram_id(from_tg_id)
    if not from_row:
        await query.answer("Сначала зарегистрируйся: /start", show_alert=True)
        return
    from_id = from_row["id"]

    added = add_like(from_id, to_user_id)
    if not added:
        await query.answer("Вы уже лайкали этого пользователя.", show_alert=True)
        return

    # проверяем матч
    match_id = check_and_create_match_if_any(from_id, to_user_id)
    # сообщение для кликнувшего
    await query.answer("Лайк отправлен!")

    # покажем следующую карточку (простая логика: используем /browse команду — но лучше показать следующую прямо)
    # Попытаемся показать следующую карточку - emulate by editing or just send a hint
    await query.message.answer("Показываю следующую анкету...")
    # получили match -> уведомляем обе стороны
    if match_id:
        # получаем профили
        a = get_user_by_id(from_id)
        b = get_user_by_id(to_user_id)
        # составим текст сообщений
        text_for_a = (f"У вас матч! 👏\n\nПрофиль партнёра:\n"
                      f"{b['gender'].title()}, {b['age']} лет\n{b['city']}\nЦель: {b['target']}\n\n{b['bio']}\n\n"
                      f"Открыть чат: tg://user?id={b['telegram_id']}")
        text_for_b = (f"У вас матч! 👏\n\nПрофиль партнёра:\n"
                      f"{a['gender'].title()}, {a['age']} лет\n{a['city']}\nЦель: {a['target']}\n\n{a['bio']}\n\n"
                      f"Открыть чат: tg://user?id={a['telegram_id']}")

        # отправляем сообщения (через бота) — используем метод bot.send_message
        await query.message.bot.send_message(chat_id=a["telegram_id"], text=text_for_a)
        await query.message.bot.send_message(chat_id=b["telegram_id"], text=text_for_b)

@router.callback_query(lambda c: c.data and c.data.startswith("skip:"))
async def callback_skip(query: CallbackQuery):
    # простое поведение: ответить и посоветовать снова нажать /browse
    await query.answer("Пропущено.")
    await query.message.answer("Если хочешь — продолжай: /browse")
