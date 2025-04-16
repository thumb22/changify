import logging
import traceback
from functools import wraps
from aiogram import types
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TelegramAPIError as e:
            logger.error(f"Telegram API Error: {e}")
            for arg in args:
                if isinstance(arg, types.Message):
                    await arg.answer("Произошла ошибка при обработке запроса. Попробуйте позже.")
                    break
        except Exception as e:
            error_msg = f"Необработанная ошибка: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            for arg in args:
                if isinstance(arg, types.Message):
                    await arg.answer("Что-то пошло не так. Попробуйте позже или обратитесь в поддержку.")
                    break
    return wrapper