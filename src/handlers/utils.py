from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.models.models import CategoryModel, UserModel, TaskModel, ReminderModel


# ==============================
# Пользователи
# ==============================

async def get_or_create_user(db_session: AsyncSession, user_data) -> UserModel:
    """Получает или создает пользователя."""
    async with db_session.begin():
        stmt = select(UserModel).where(UserModel.user_id == user_data.id)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            new_user = UserModel(
                user_id=user_data.id,
                username=user_data.username
            )
            db_session.add(new_user)
            return new_user

        return user


# ==============================
# Категории
# ==============================

async def get_user_categories(db_session: AsyncSession, user_id: int) -> list[CategoryModel]:
    """Получает категории пользователя."""
    async with db_session.begin():
        category_stmt = select(CategoryModel).where(CategoryModel.user_id == user_id)
        category_result = await db_session.execute(category_stmt)
        categories = category_result.scalars().all()

    return categories


async def get_or_create_category(db_session: AsyncSession, category_name: str, user_id: int) -> tuple[CategoryModel, bool]:
    """Получает или создает категорию для данного пользователя."""
    async with db_session.begin():
        category_stmt = select(CategoryModel).where(
            CategoryModel.name == category_name,
            CategoryModel.user_id == user_id
        )
        category_result = await db_session.execute(category_stmt)
        existing_category = category_result.scalar_one_or_none()

        if existing_category is None:
            new_category = CategoryModel(
                name=category_name,
                user_id=user_id
            )
            db_session.add(new_category)
            await db_session.commit()
            return new_category, True

        return existing_category, False


async def delete_category(db_session: AsyncSession, category_id: int, user_id: int) -> None:
    """Удаляет категорию по идентификатору для данного пользователя."""
    async with db_session.begin():
        category_query = select(CategoryModel).where(
            CategoryModel.id == category_id,
            CategoryModel.user_id == user_id
        )

        result = await db_session.execute(category_query)
        category = result.scalar_one_or_none()

        if category is None:
            raise ValueError(f"Категория с ID '{category_id}' не найдена.")

        tasks_query = select(TaskModel).where(TaskModel.category_id == category.id)
        tasks_result = await db_session.execute(tasks_query)

        tasks = tasks_result.scalars().all()
        for task in tasks:
            await db_session.delete(task)

        await db_session.delete(category)


async def update_category(db_session: AsyncSession, category_id, new_name, user_id):
    """Обновляет название категории по идентификатору для данного пользователя."""
    async with db_session.begin():
        category_query = select(CategoryModel).where(
            CategoryModel.id == category_id,
            CategoryModel.user_id == user_id
        )

        result = await db_session.execute(category_query)
        category = result.scalar_one_or_none()

        if category:
            category.name = new_name
        else:
            raise ValueError(f"Категория с ID '{category_id}' не найдена.")


# ==============================
# Напоминания
# ==============================

async def create_task(db_session: AsyncSession, description: str, category_id: int, user_id: int) -> TaskModel:
    """Создает новую задачу."""
    async with db_session.begin():
        new_task = TaskModel(
            description=description,
            category_id=category_id,
            user_id=user_id
        )
        db_session.add(new_task)

    return new_task


async def get_tasks(db_session: AsyncSession, user_id: int) -> list[TaskModel]:
    """Получает все задачи с именами категорий."""
    async with db_session.begin():
        tasks_stmt = (
            select(TaskModel)
            .options(joinedload(TaskModel.category))
            .where(TaskModel.user_id == user_id)
        )
        tasks_result = await db_session.execute(tasks_stmt)
        tasks = tasks_result.scalars().all()

    return tasks


def format_tasks_by_category(tasks: list[TaskModel]) -> str:
    """Форматирует задачи по категориям."""
    tasks_by_category = {}

    for task in tasks:
        category_name = task.category.name
        if category_name not in tasks_by_category:
            tasks_by_category[category_name] = []
        tasks_by_category[category_name].append(task.description)

    tasks_message = "<b>Ваши напоминания:</b>\n\n"
    for category, descriptions in tasks_by_category.items():
        tasks_message += f"<b>{category}:</b>\n"
        for idx, description in enumerate(descriptions, start=1):
            tasks_message += f"{idx}. {description}\n"
        tasks_message += "\n"

    return tasks_message


async def delete_task_by_id(db_session: AsyncSession, task_id: int, user_id: int) -> None:
    """Удаляет напоминание по ID для данного пользователя."""
    async with db_session.begin():
        task_query = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.user_id == user_id
        )
        result = await db_session.execute(task_query)
        task = result.scalar_one_or_none()

        if task:
            await db_session.delete(task)
        else:
            raise ValueError(f"Напоминание с ID '{task_id}' не найдено.")


async def add_reminder(db_session: AsyncSession, date, description, user_id) -> bool:
    """Добавляет событие в базу данных."""
    async with db_session.begin():
        new_reminder = ReminderModel(date=date, description=description, user_id=user_id)

        try:
            db_session.add(new_reminder)
            return True
        except SQLAlchemyError:
            await db_session.rollback()
            return False


async def get_reminders(db_session: AsyncSession, user_id: int) -> list[ReminderModel]:
    """Получает все события пользователя."""
    async with db_session.begin():
        reminders_stmt = (
            select(ReminderModel)
            .where(ReminderModel.user_id == user_id)
        )

        reminders_result = await db_session.execute(reminders_stmt)
        reminders = reminders_result.scalars().all()

    return reminders


async def delete_reminder_by_id(db_session: AsyncSession, reminder_id: int, user_id: int) -> None:
    """Удаляет событие по ID для данного пользователя."""
    async with db_session.begin():
        reminder_query = select(ReminderModel).where(
            ReminderModel.id == reminder_id,
            ReminderModel.user_id == user_id
        )
        result = await db_session.execute(reminder_query)
        reminder = result.scalar_one_or_none()

        if reminder:
            await db_session.delete(reminder)
        else:
            raise ValueError(f"Напоминание с ID '{reminder_id}' не найдено.")
