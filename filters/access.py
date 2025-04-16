from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from database.models import UserRole
import logging

logger = logging.getLogger(__name__)

class AdminFilter(BaseFilter):
    """
    Фильтр для проверки прав администратора
    """
    async def __call__(self, event):
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            if not hasattr(event, 'db_user'):
                return False
            
            db_user = event.db_user
            return db_user and db_user['role'] == UserRole.ADMIN
        return False

class ManagerFilter(BaseFilter):
    """
    Фильтр для проверки прав менеджера (менеджер или администратор)
    """
    async def __call__(self, event):
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            if not hasattr(event, 'db_user'):
                return False
            
            db_user = event.db_user
            return db_user and (db_user['role'] == UserRole.MANAGER or db_user['role'] == UserRole.ADMIN)
        return False

class UserFilter(BaseFilter):
    """
    Фильтр для проверки прав обычного пользователя
    """
    async def __call__(self, event):
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            if not hasattr(event, 'db_user'):
                return False
            
            db_user = event.db_user
            return bool(db_user)
        return False