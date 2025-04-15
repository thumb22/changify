from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard():
    """
    Створює основну клавіатуру для користувача
    """
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="🔄 Обмін валют"),
        KeyboardButton(text="📊 Курси валют")
    )
    
    builder.row(
        KeyboardButton(text="📋 Історія"),
        KeyboardButton(text="👤 Профіль")
    )
    
    builder.row(KeyboardButton(text="🆘 Підтримка"))
    
    return builder.as_markup(resize_keyboard=True)


def get_manager_keyboard():
    """
    Створює клавіатуру для менеджера
    """
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="📝 Заявки"),
        KeyboardButton(text="✅ Завершені")
    )
    
    builder.row(
        KeyboardButton(text="📈 Статистика"),
        KeyboardButton(text="👤 Профіль")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_admin_keyboard():
    """
    Створює клавіатуру для адміністратора
    """
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="📝 Заявки"),
        KeyboardButton(text="👥 Користувачі")
    )
    
    builder.row(
        KeyboardButton(text="💱 Курси валют"),
        KeyboardButton(text="⚙️ Налаштування")
    )
    
    builder.row(KeyboardButton(text="📊 Статистика"))
    
    return builder.as_markup(resize_keyboard=True)