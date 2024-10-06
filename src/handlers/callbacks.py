import datetime

from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from keyboards.keyboards import (
    task_keyboard,
    generate_category_keyboard,
    main_menu_keyboard,
    generate_task_keyboard_for_deletion,
    back_keyboard, generate_reminder_keyboard
)
from .router import callbacks_router
from .states import InputState
from .text_constants import BOT_ANSWER
from .utils import (
    get_or_create_category,
    create_task,
    get_tasks,
    delete_category,
    delete_task_by_id,
    format_tasks_by_category,
    update_category, add_reminder, get_reminders, delete_reminder_by_id
)


async def send_message_with_keyboard(callback_query: CallbackQuery, text: str, reply_markup) -> None:
    """Помощник для редактирования сообщений и отправки клавиатуры."""
    await callback_query.message.edit_text(text, reply_markup=reply_markup)
    await callback_query.answer()


async def handle_database_error(callback_query: CallbackQuery, error_message: str) -> None:
    """Обрабатывает ошибки, отправляя сообщение об ошибке."""
    await send_message_with_keyboard(callback_query, error_message, main_menu_keyboard)


# ==============================
# Главное меню
# ==============================

@callbacks_router.callback_query(lambda c: c.data == "main_menu_pressed")
async def open_menu(callback_query: CallbackQuery) -> None:
    """Открывает главное меню"""
    await send_message_with_keyboard(callback_query, BOT_ANSWER["menu_tasks"], task_keyboard)


@callbacks_router.callback_query(lambda c: c.data == "back_pressed")
async def handle_back_button(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Возвращает пользователя в главное меню и сбрасывает состояние."""
    await state.clear()
    await send_message_with_keyboard(callback_query, BOT_ANSWER["menu_tasks"], task_keyboard)


# ==============================
# Работа с категориями
# ==============================

@callbacks_router.callback_query(lambda c: c.data == "add_category_pressed")
async def input_category_name(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает название категории"""
    await send_message_with_keyboard(callback_query, BOT_ANSWER["input_category_name"], back_keyboard)
    await state.update_data(deleting_category=False)
    await state.set_state(InputState.waiting_for_category_name)


@callbacks_router.callback_query(lambda c: c.data == "delete_category_pressed")
async def show_category_keyboard_for_deletion(callback_query: CallbackQuery, state: FSMContext,
                                              db_session: AsyncSession) -> None:
    """Показывает клавиатуру с категориями для удаления"""
    user_id = callback_query.from_user.id
    category_keyboard = await generate_category_keyboard(user_id, db_session)
    await send_message_with_keyboard(callback_query, BOT_ANSWER["input_category_name_for_delete"], category_keyboard)
    await state.set_state(InputState.waiting_for_category_deletion)


@callbacks_router.callback_query(
    StateFilter(InputState.waiting_for_category_deletion), lambda c: c.data.startswith("category_"))
async def delete_selected_category(callback_query: CallbackQuery, state: FSMContext, db_session: AsyncSession) -> None:
    """Удаляет выбранную категорию"""
    category_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id

    try:
        await delete_category(db_session, category_id, user_id)
        await send_message_with_keyboard(callback_query, BOT_ANSWER["category_deleted"], main_menu_keyboard)
    except SQLAlchemyError:
        await handle_database_error(callback_query, BOT_ANSWER["error_occurred"])

    await state.clear()


@callbacks_router.message(StateFilter(InputState.waiting_for_category_name))
async def handle_category_name(message: Message, state: FSMContext, db_session: AsyncSession) -> None:
    """Добавляет новую категорию или удаляет существующую"""
    category_name = message.text
    user_id = message.from_user.id
    data = await state.get_data()

    try:
        if data.get("deleting_category", False):
            await delete_category(db_session, category_name, user_id)
            await message.answer(BOT_ANSWER["category_deleted"].format(category_name=category_name),
                                 reply_markup=main_menu_keyboard)
            await state.update_data(deleting_category=False)
        else:
            category, created = await get_or_create_category(db_session, category_name, user_id)

            if created:
                await message.answer(BOT_ANSWER["category_added"].format(category_name=category_name),
                                     reply_markup=task_keyboard)
            else:
                await message.answer(BOT_ANSWER["category_exists"].format(category_name=category_name),
                                     reply_markup=main_menu_keyboard)
    except SQLAlchemyError:
        await message.answer(BOT_ANSWER["error_occurred"], reply_markup=main_menu_keyboard)

    await state.clear()


@callbacks_router.callback_query(lambda c: c.data == "update_category_pressed")
async def show_category_keyboard_for_update(callback_query: CallbackQuery, state: FSMContext,
                                            db_session: AsyncSession) -> None:
    """Показывает клавиатуру с категориями для изменения"""
    user_id = callback_query.from_user.id
    category_keyboard = await generate_category_keyboard(user_id, db_session)

    await send_message_with_keyboard(callback_query, BOT_ANSWER["input_category_name_for_update"], category_keyboard)
    await state.set_state(InputState.waiting_for_category_update)


@callbacks_router.callback_query(
    StateFilter(InputState.waiting_for_category_update), lambda c: c.data.startswith("category_"))
async def input_new_category_name(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает новое название выбранной категории"""
    category_id = int(callback_query.data.split("_")[1])
    await state.update_data(current_category_id=category_id)

    await send_message_with_keyboard(callback_query, BOT_ANSWER["input_new_category_name"], back_keyboard)
    await state.set_state(InputState.waiting_for_new_category_name)


@callbacks_router.message(StateFilter(InputState.waiting_for_new_category_name))
async def update_category_name(message: Message, state: FSMContext, db_session: AsyncSession) -> None:
    """Обновляет название категории"""
    new_category_name = message.text
    user_id = message.from_user.id
    data = await state.get_data()
    category_id = data.get("current_category_id")

    try:
        await update_category(db_session, category_id, new_category_name, user_id)
        await message.answer(BOT_ANSWER["category_updated"].format(category_name=new_category_name),
                             reply_markup=main_menu_keyboard)
    except SQLAlchemyError:
        await message.answer(BOT_ANSWER["error_occurred"], reply_markup=main_menu_keyboard)

    await state.clear()


# ==============================
# Работа с задачами
# ==============================

@callbacks_router.callback_query(lambda c: c.data == "add_task_pressed")
async def select_category_for_add_task(callback_query: CallbackQuery, db_session: AsyncSession) -> None:
    """Выбор категории для задачи"""
    user_id = callback_query.from_user.id
    category_keyboard = await generate_category_keyboard(user_id, db_session)

    await send_message_with_keyboard(callback_query, BOT_ANSWER["select_category_for_task"], category_keyboard)


@callbacks_router.callback_query(lambda c: c.data.startswith("category_"))
async def input_description_task(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает описание задачи"""
    category_id = int(callback_query.data.split("_")[1])
    await state.update_data(current_category_id=category_id)

    await send_message_with_keyboard(callback_query, BOT_ANSWER["input_task_description"], back_keyboard)
    await state.set_state(InputState.waiting_for_task_description)


@callbacks_router.message(StateFilter(InputState.waiting_for_task_description))
async def add_task(message: Message, state: FSMContext, db_session: AsyncSession) -> None:
    """Добавляет новую задачу"""
    task_description = message.text
    user_id = message.from_user.id
    category_id = (await state.get_data()).get("current_category_id")

    try:
        await create_task(db_session, task_description, category_id, user_id)
        await message.answer(BOT_ANSWER["task_added"].format(task_description=task_description),
                             reply_markup=main_menu_keyboard)
    except SQLAlchemyError:
        await message.answer(BOT_ANSWER["error_occurred"], reply_markup=main_menu_keyboard)

    await state.clear()


@callbacks_router.callback_query(lambda c: c.data == "get_task_pressed")
async def get_all_tasks(callback_query: CallbackQuery, db_session: AsyncSession) -> None:
    """Получает все задачи пользователя"""
    user_id = callback_query.from_user.id

    tasks = await get_tasks(db_session, user_id)

    if tasks:
        tasks_message = format_tasks_by_category(tasks)
        await send_message_with_keyboard(callback_query, tasks_message, main_menu_keyboard)
    else:
        await send_message_with_keyboard(callback_query, BOT_ANSWER["no_tasks"], main_menu_keyboard)


@callbacks_router.callback_query(lambda c: c.data == "delete_task_pressed")
async def show_task_keyboard_for_deletion(callback_query: CallbackQuery, db_session: AsyncSession) -> None:
    """Показывает клавиатуру с задачами для удаления"""
    user_id = callback_query.from_user.id

    tasks = await get_tasks(db_session, user_id)
    if tasks:
        task_keyboard = await generate_task_keyboard_for_deletion(tasks)
        await send_message_with_keyboard(callback_query, BOT_ANSWER["select_task_to_delete"], task_keyboard)
    else:
        await send_message_with_keyboard(callback_query, BOT_ANSWER["no_tasks"], main_menu_keyboard)


@callbacks_router.callback_query(lambda c: c.data.startswith("task_"))
async def delete_selected_task(callback_query: CallbackQuery, db_session: AsyncSession) -> None:
    """Удаляет выбранную задачу"""
    user_id = callback_query.from_user.id
    task_id = int(callback_query.data.split("_")[1])

    try:
        await delete_task_by_id(db_session, task_id, user_id)
        await send_message_with_keyboard(callback_query, BOT_ANSWER["task_deleted"], main_menu_keyboard)
    except SQLAlchemyError:
        await handle_database_error(callback_query, BOT_ANSWER["error_occurred"])


# ==============================
# Напоминания
# ==============================

@callbacks_router.callback_query(lambda c: c.data == "add_date")
async def input_reminder_data(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает данные для напоминания"""
    await send_message_with_keyboard(callback_query, BOT_ANSWER["input_date_and_description"], back_keyboard)
    await state.set_state(InputState.waiting_for_reminder_input)


@callbacks_router.message(StateFilter(InputState.waiting_for_reminder_input))
async def add_reminder_data(message: Message, state: FSMContext, db_session: AsyncSession) -> None:
    """Обрабатывает текст и дату напоминания"""
    user_id = message.from_user.id
    user_input = message.text.strip()

    try:
        date, text = user_input.split(' ', 1)
        clean_date = datetime.datetime.strptime(date, "%d.%m.%Y")

        await add_reminder(db_session, clean_date, text, user_id)

        await message.answer(BOT_ANSWER["reminder_added"].format(reminder_text=text),
                             reply_markup=main_menu_keyboard)
    except ValueError:
        await message.answer(BOT_ANSWER["invalid_format"],
                             reply_markup=main_menu_keyboard)
    except SQLAlchemyError:
        await handle_database_error(message, BOT_ANSWER["error_occurred"])

    await state.clear()


@callbacks_router.callback_query(lambda c: c.data == "get_dates_pressed")
async def get_all_reminders(callback_query: CallbackQuery, db_session: AsyncSession) -> None:
    """Получает все напоминания пользователя"""
    user_id = callback_query.from_user.id

    reminders = await get_reminders(db_session, user_id)

    if reminders:
        reminders_message = "\n".join(
            [f"📅 <b>{reminder.date.strftime('%d.%m.%Y')}</b> - {reminder.description}" for reminder in reminders]
        )
        await send_message_with_keyboard(callback_query, reminders_message, main_menu_keyboard)
    else:
        await send_message_with_keyboard(callback_query, BOT_ANSWER["no_reminders"], main_menu_keyboard)


@callbacks_router.callback_query(lambda c: c.data == "delete_date_pressed")
async def show_reminders_keyboard_for_deletion(callback_query: CallbackQuery, db_session: AsyncSession) -> None:
    """Показывает клавиатуру с напоминаниями для удаления"""
    user_id = callback_query.from_user.id

    reminders = await get_reminders(db_session, user_id)
    if reminders:
        reminders_keyboard = await generate_reminder_keyboard(reminders)
        await send_message_with_keyboard(callback_query, BOT_ANSWER["select_reminder_to_delete"], reminders_keyboard)
    else:
        await send_message_with_keyboard(callback_query, BOT_ANSWER["no_reminders"], main_menu_keyboard)


@callbacks_router.callback_query(lambda c: c.data.startswith("reminder_"))
async def delete_selected_reminder(callback_query: CallbackQuery, db_session: AsyncSession) -> None:
    """Удаляет выбранное напоминание"""
    reminder_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id

    try:
        await delete_reminder_by_id(db_session, reminder_id, user_id)
        await send_message_with_keyboard(callback_query, BOT_ANSWER["reminder_deleted"], main_menu_keyboard)
    except SQLAlchemyError:
        await handle_database_error(callback_query, BOT_ANSWER["error_occurred"])


@callbacks_router.message()
async def unknown_message(message: Message, state: FSMContext):
    """Обрабатывает все неизвестные текстовые сообщения"""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(BOT_ANSWER["other_messages"], reply_markup=main_menu_keyboard)