from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.keyboards import main_menu_keyboard
from .router import commands_router
from .text_constants import BOT_ANSWER

from .utils import get_or_create_user


async def send_welcome_message(user, message):
    username = user.username if user.username else user.first_name
    await message.answer(
        text=BOT_ANSWER["welcome"].format(username=username),
        reply_markup=main_menu_keyboard
    )


@commands_router.message(CommandStart())
async def processed_start_command(message: Message, db_session: AsyncSession):
    user_data = message.from_user

    user = await get_or_create_user(db_session, user_data)
    await send_welcome_message(user, message)

@commands_router.message(Command(commands=["help"]))
async def processed_help_command(message: Message):
    await message.answer(BOT_ANSWER["help"])