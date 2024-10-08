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
    db_session = await get_session()
    try:
        stmt = select(UserModel)
        result = await db_session.execute(stmt)
        return result.scalars().all()
    finally:
        await db_session.close()


async def send_task_message(user_id: int, bot: Bot) -> None:
    db_session = await get_session()
    try:
        tasks = await get_tasks(db_session, user_id)
        if tasks:
            tasks_message = format_tasks_by_category(tasks)
            await bot.send_message(user_id, tasks_message, parse_mode='HTML', reply_markup=main_menu_keyboard)
    finally:
        await db_session.close()


async def get_reminders_for_user(db_session, user_id, target_date):
    start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(
        timezone('Europe/Moscow')).replace(tzinfo=None)
    end_date = (start_date + timedelta(days=1)).replace(tzinfo=None)

    stmt = select(ReminderModel).where(
        ReminderModel.user_id == user_id,
        ReminderModel.date >= start_date,
        ReminderModel.date < end_date
    )
    result = await db_session.execute(stmt)
    return result.scalars().all()


async def notify_user_about_today_reminders(user_id: int, bot: Bot) -> None:
    db_session = await get_session()
    try:
        today = datetime.now(timezone('Europe/Moscow')).astimezone(timezone('Europe/Moscow'))

        reminders_today = await get_reminders_for_user(db_session, user_id, today)

        if reminders_today:
            reminders_message = "📅 <b>Сегодня:</b>\n" + "\n".join(
                [f"- {reminder.date.strftime('%d.%m.%Y')}: {reminder.description}" for reminder in reminders_today]
            )
            await bot.send_message(user_id, reminders_message, parse_mode='HTML', reply_markup=main_menu_keyboard)
    finally:
        await db_session.close()


# Уведомляем пользователя о конкретном напоминании
async def notify_user_about_event_reminders(user_id: int, bot: Bot, reminder: ReminderModel) -> None:
    reminders_message = f"📅 <b>Напоминание на {reminder.date.strftime('%d.%m.%Y')}:</b>\n- {reminder.description}"
    await bot.send_message(user_id, reminders_message, parse_mode='HTML', reply_markup=main_menu_keyboard)


async def check_and_notify_reminders(bot: Bot) -> None:
    db_session = await get_session()
    try:
        users = await get_all_users()
        for user in users:
            await notify_user_about_today_reminders(user.user_id, bot)
    finally:
        await db_session.close()


async def start_task_scheduler(bot: Bot) -> None:
    db_session = await get_session()
    try:
        users = await get_all_users()

        for user in users:
            scheduler.add_job(
                send_task_message,
                CronTrigger(hour=20, minute=0, timezone='Europe/Moscow'),
                args=[user.user_id, bot]
            )

        scheduler.start()
    finally:
        await db_session.close()


async def start_reminder_scheduler(bot: Bot) -> None:
    scheduler.add_job(
        check_and_notify_reminders,
        CronTrigger(hour=9, minute=0, timezone='Europe/Moscow'),
        args=[bot]
    )


async def start_schedulers(bot: Bot) -> None:
    await start_task_scheduler(bot)
    await start_reminder_scheduler(bot)
