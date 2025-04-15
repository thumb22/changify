import logging
import traceback
from functools import wraps
from aiogram import types
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

def handle_errors(func):
    """
    Декоратор для обработки ошибок в хэндлерах
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TelegramAPIError as e:
            # Ошибки API Telegram
            logger.error(f"Telegram API Error: {e}")
            # Пытаемся получить объект сообщения для ответа пользователю
            for arg in args:
                if isinstance(arg, types.Message):
                    await arg.answer("Произошла ошибка при обработке запроса. Попробуйте позже.")
                    break
        except Exception as e:
            # Прочие ошибки
            error_msg = f"Необработанная ошибка: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            # Пытаемся получить объект сообщения для ответа пользователю
            for arg in args:
                if isinstance(arg, types.Message):
                    await arg.answer("Что-то пошло не так. Попробуйте позже или обратитесь в поддержку.")
                    break
    return wrapper