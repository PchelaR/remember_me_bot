from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.utils import get_user_categories
from models.models import ReminderModel
from .menu_items import menu_buttons, main_menu_buttons, category_buttons, task_buttons, reminder_buttons


def back_button():
    return InlineKeyboardButton(text="🚫 Отмена", callback_data="back_pressed")


back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button()]])

# Формируем главное меню
main_menu_list = list(menu_buttons.values())
task_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback)] for text, callback in main_menu_list
    ]
)

# Формируем меню для работы с категориями
category_menu_list = list(category_buttons.values())
category_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
                        [InlineKeyboardButton(text=text, callback_data=callback)] for text, callback in
                        category_menu_list
                    ] + [[back_button()]]
)

# Формируем меню для работы с напоминаниями
task_menu_list = list(task_buttons.values())
task_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
                        [InlineKeyboardButton(text=text, callback_data=callback)] for text, callback in task_menu_list
                    ] + [[back_button()]]
)

# Формируем меню для работы с событиями
reminder_menu_list = list(reminder_buttons.values())
reminder_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
                        [InlineKeyboardButton(text=text, callback_data=callback)] for text, callback in
                        reminder_menu_list
                    ] + [[back_button()]]
)

main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback)] for text, callback in main_menu_buttons.values()
    ]
)


async def generate_category_keyboard(user_id, db_session: AsyncSession):
    categories = await get_user_categories(db_session, user_id)

    category_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text=category.name, callback_data=f"category_{category.id}")]
                            for category in categories
                        ] + [[back_button()]]
    )

    return category_keyboard


async def generate_task_keyboard_for_deletion(tasks):
    return InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text=task.description, callback_data=f"task_{task.id}")]
                            for task in tasks
                        ] + [[back_button()]]
    )


async def generate_reminder_keyboard(reminders: list[ReminderModel]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для напоминаний."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"{reminder.date.strftime('%d.%m.%Y')} - {reminder.description}",
                                callback_data=f"reminder_{reminder.id}"
                            )] for reminder in reminders
                        ] + [[back_button()]]
    )

    return keyboard
