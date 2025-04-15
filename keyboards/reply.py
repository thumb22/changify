# keyboards/reply.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_keyboard(language="uk"):
    """
    Создает основную клавиатуру для пользователя в зависимости от выбранного языка
    """
    # Локализация кнопок
    button_texts = {
        "uk": {
            "exchange": "🔄 Обмін валют",
            "rates": "📊 Курси валют",
            "history": "📋 Iсторія",
            "profile": "👤 Профіль",
            "support": "🆘 Підтримка"
        },
        "en": {
            "exchange": "🔄 Exchange",
            "rates": "📊 Rates",
            "history": "📋 History",
            "profile": "👤 Profile",
            "support": "🆘 Support"
        },
        "ru": {
            "exchange": "🔄 Обмен валют",
            "rates": "📊 Курсы валют",
            "history": "📋 История",
            "profile": "👤 Профиль",
            "support": "🆘 Поддержка"
        }
    }
    
    # Выбираем нужный язык или дефолтный
    lang_buttons = button_texts.get(language, button_texts["uk"])
    
    builder = ReplyKeyboardBuilder()
    
    # Добавляем кнопки в первый ряд
    builder.row(
        KeyboardButton(text=lang_buttons["exchange"]),
        KeyboardButton(text=lang_buttons["rates"])
    )
    
    # Добавляем кнопки во второй ряд
    builder.row(
        KeyboardButton(text=lang_buttons["history"]),
        KeyboardButton(text=lang_buttons["profile"])
    )
    
    # Добавляем кнопку поддержки
    builder.row(KeyboardButton(text=lang_buttons["support"]))
    
    return builder.as_markup(resize_keyboard=True)


def get_manager_keyboard(language="uk"):
    """
    Создает клавиатуру для менеджера
    """
    # Локализация кнопок
    button_texts = {
        "uk": {
            "orders": "📝 Заявки",
            "completed": "✅ Завершені",
            "stats": "📈 Статистика",
            "profile": "👤 Профіль"
        },
        "en": {
            "orders": "📝 Orders",
            "completed": "✅ Completed",
            "stats": "📈 Statistics",
            "profile": "👤 Profile"
        },
        "ru": {
            "orders": "📝 Заявки",
            "completed": "✅ Завершенные",
            "stats": "📈 Статистика",
            "profile": "👤 Профиль"
        }
    }
    
    # Выбираем нужный язык или дефолтный
    lang_buttons = button_texts.get(language, button_texts["uk"])
    
    builder = ReplyKeyboardBuilder()
    
    # Добавляем кнопки в первый ряд
    builder.row(
        KeyboardButton(text=lang_buttons["orders"]),
        KeyboardButton(text=lang_buttons["completed"])
    )
    
    # Добавляем кнопки во второй ряд
    builder.row(
        KeyboardButton(text=lang_buttons["stats"]),
        KeyboardButton(text=lang_buttons["profile"])
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_admin_keyboard(language="uk"):
    """
    Создает клавиатуру для администратора
    """
    # Локализация кнопок
    button_texts = {
        "uk": {
            "orders": "📝 Заявки",
            "users": "👥 Користувачі",
            "rates": "💱 Курси валют",
            "settings": "⚙️ Налаштування",
            "stats": "📊 Статистика"
        },
        "en": {
            "orders": "📝 Orders",
            "users": "👥 Users",
            "rates": "💱 Exchange Rates",
            "settings": "⚙️ Settings",
            "stats": "📊 Statistics"
        },
        "ru": {
            "orders": "📝 Заявки",
            "users": "👥 Пользователи",
            "rates": "💱 Курсы валют",
            "settings": "⚙️ Настройки",
            "stats": "📊 Статистика"
        }
    }
    
    # Выбираем нужный язык или дефолтный
    lang_buttons = button_texts.get(language, button_texts["uk"])
    
    builder = ReplyKeyboardBuilder()
    
    # Добавляем кнопки в первый ряд
    builder.row(
        KeyboardButton(text=lang_buttons["orders"]),
        KeyboardButton(text=lang_buttons["users"])
    )
    
    # Добавляем кнопки во второй ряд
    builder.row(
        KeyboardButton(text=lang_buttons["rates"]),
        KeyboardButton(text=lang_buttons["settings"])
    )
    
    # Добавляем кнопку статистики
    builder.row(KeyboardButton(text=lang_buttons["stats"]))
    
    return builder.as_markup(resize_keyboard=True)