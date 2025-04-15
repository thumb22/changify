from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database.db_operations import get_session, get_or_create_user
from database.models import UserRole
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserMiddleware(BaseMiddleware):
    """
    Промежуточное ПО для проверки и создания пользователей
    """
    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Извлекаем объект пользователя Telegram
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if not user:
            logger.warning("No user found in event")
            return await handler(event, data)
        
        try:
            # Получаем или создаем пользователя в базе данных
            with get_session(self.engine) as session:
                user_data = {
                    'telegram_id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'last_active': datetime.utcnow()
                }
                
                db_user = get_or_create_user(session, user_data)
                # Ensure the session commits any changes
                session.commit()
                
                # Detach the object from the session by converting to a dictionary or copying attributes
                db_user_data = {
                    'telegram_id': db_user.telegram_id,
                    'username': db_user.username,
                    'first_name': db_user.first_name,
                    'last_name': db_user.last_name,
                    'role': db_user.role,
                    'last_active': db_user.last_active
                }
                
                # Добавляем объект пользователя в контекст
                data['db_user'] = db_user_data
                
                logger.debug(f"Пользователь {user.id} (роль: {db_user.role.name}) обработан middleware")
                
        except Exception as e:
            logger.error(f"Ошибка в UserMiddleware: {e}", exc_info=True)
            # Provide a fallback user with default role
            data['db_user'] = {
                'telegram_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': UserRole.USER,
                'last_active': datetime.utcnow()
            }
        
        return await handler(event, data)