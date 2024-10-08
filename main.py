import os
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram import Dispatcher

from handlers.commands import commands_router
from handlers.callbacks import callbacks_router
from config import BOT_TOKEN

from handlers.scheduler import start_schedulers
from middleware import DatabaseSessionMiddleware
from menus.menus import set_main_menu

os.environ['TZ'] = 'Europe/Moscow'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    dp.message.middleware(DatabaseSessionMiddleware())
    dp.callback_query.middleware(DatabaseSessionMiddleware())

    dp.include_router(commands_router)
    dp.include_router(callbacks_router)

    await set_main_menu(bot)

    await bot.delete_webhook(drop_pending_updates=True)

    await start_schedulers(bot)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
