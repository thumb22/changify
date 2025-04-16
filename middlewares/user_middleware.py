from typing import Any, Awaitable, Callable, Dict
from zoneinfo import ZoneInfo
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database.db_operations import get_session, get_or_create_user
from database.models import UserRole
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

def sanitize(text: str | None) -> str:
    return text.strip() if text else ""

class UserMiddleware(BaseMiddleware):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user or not user.id:
            logger.warning("Invalid or missing user in event")
            return await handler(event, data)

        try:
            with get_session(self.engine) as session:
                data['session'] = session

                user_data = {
                    'telegram_id': user.id,
                    'username': sanitize(user.username),
                    'first_name': sanitize(user.first_name),
                    'last_name': sanitize(user.last_name),
                    'last_active': datetime.now(ZoneInfo("Europe/Kyiv"))
                }

                db_user = get_or_create_user(session, user_data)
                session.commit()

                data['db_user'] = {
                    'telegram_id': db_user.telegram_id,
                    'username': db_user.username,
                    'first_name': db_user.first_name,
                    'last_name': db_user.last_name,
                    'role': db_user.role,
                    'last_active': db_user.last_active,
                    'created_at': db_user.created_at
                }

                logger.info(f"UserMiddleware processed user ID {user.id} with role {db_user.role.name}")

        except SQLAlchemyError as db_err:
            logger.error(f"Database error in UserMiddleware: {db_err}", exc_info=True)
        except Exception as e:
            logger.exception("Unexpected error in UserMiddleware")

        if 'db_user' not in data:
            data['db_user'] = {
                'telegram_id': user.id,
                'username': sanitize(user.username),
                'first_name': sanitize(user.first_name),
                'last_name': sanitize(user.last_name),
                'role': UserRole.USER,
                'last_active': datetime.now(ZoneInfo("Europe/Kyiv"))
            }

        return await handler(event, data)
