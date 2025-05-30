from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from database.models import UserRole
import logging

logger = logging.getLogger(__name__)

class AdminFilter(BaseFilter):
    async def __call__(self, event):
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            if not hasattr(event, 'db_user'):
                return False
            
            db_user = event.db_user
            return db_user and db_user['role'] == UserRole.ADMIN
        return False

class ManagerFilter(BaseFilter):
    async def __call__(self, event):
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            if not hasattr(event, 'db_user'):
                return False
            
            db_user = event.db_user
            return db_user and (db_user['role'] == UserRole.MANAGER or db_user['role'] == UserRole.ADMIN)
        return False

class UserFilter(BaseFilter):
    async def __call__(self, event):
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            if not hasattr(event, 'db_user'):
                return False
            
            db_user = event.db_user
            return bool(db_user)
        return False