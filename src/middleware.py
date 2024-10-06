from aiogram import BaseMiddleware
from database import get_session


class DatabaseSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        session = await get_session()
        async with session as db_session:
            data['db_session'] = db_session
            return await handler(event, data)
