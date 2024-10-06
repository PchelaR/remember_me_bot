from datetime import timedelta, datetime

from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from sqlalchemy.future import select

from database import get_session
from keyboards.keyboards import main_menu_keyboard
from src.models.models import UserModel, ReminderModel
from .callbacks import get_tasks, format_tasks_by_category

scheduler = AsyncIOScheduler(timezone=timezone('Europe/Moscow'))


async def get_all_users() -> list:
    """Получает всех пользователей из базы данных."""
    db_session = await get_session()
    try:
        stmt = select(UserModel)
        result = await db_session.execute(stmt)

        users = result.scalars().all()
        return users
    except Exception as e:
        raise
    finally:
        await db_session.close()


async def send_task_message(user_id: int, bot: Bot) -> None:
    """Отправляет задачи пользователя."""
    db_session = await get_session()
    try:
        async with db_session.begin():
            tasks = await get_tasks(db_session, user_id)

            if tasks:
                tasks_message = format_tasks_by_category(tasks)
                await bot.send_message(user_id, tasks_message, parse_mode='HTML', reply_markup=main_menu_keyboard)
    finally:
        await db_session.close()


async def get_reminders_for_user(db_session, user_id, target_date):
    """Получает напоминания пользователя на конкретную дату."""
    async with db_session.begin():
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        end_date = (start_date + timedelta(days=1)).replace(tzinfo=None)

        stmt = select(ReminderModel).where(
            ReminderModel.user_id == user_id,
            ReminderModel.date >= start_date,
            ReminderModel.date < end_date
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()


async def notify_user_about_today_reminders(user_id: int, bot: Bot) -> None:
    """Проверяет и отправляет напоминания на сегодняшний день."""
    db_session = await get_session()
    try:
        today = datetime.now(timezone('Europe/Moscow'))

        reminders_today = await get_reminders_for_user(db_session, user_id, today)

        if reminders_today:
            reminders_message = "📅 <b>Сегодня!!!:</b>\n" + "\n".join(
                [f"- {reminder.date.strftime('%d.%m.%Y')}: {reminder.description}" for reminder in reminders_today]
            )
            await bot.send_message(user_id, reminders_message, parse_mode='HTML', reply_markup=main_menu_keyboard)

    finally:
        await db_session.close()


async def start_scheduler(bot: Bot) -> None:
    """Запускает шедулер."""
    users = await get_all_users()

    for user in users:
        # Напоминания в 20:00 каждый день
        scheduler.add_job(send_task_message,
                          CronTrigger(hour=20, minute=00, timezone='Europe/Moscow'),
                          args=[user.user_id, bot])

        # Напоминания о событиях в день события, в 09:00
        scheduler.add_job(notify_user_about_today_reminders,
                          CronTrigger(hour=9, minute=00, timezone='Europe/Moscow'),
                          args=[user.user_id, bot])

    scheduler.start()
