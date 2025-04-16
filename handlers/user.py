# handlers/user.py
from aiogram import Dispatcher, types
from aiogram.filters import Text
from aiogram.types import ReplyKeyboardMarkup
from keyboards.reply import get_main_keyboard
from utils.error_handler import handle_errors
from utils.db_utils import get_all_currencies, get_exchange_rate

async def process_rates_command(message: types.Message):
    """Обработчик для просмотра текущих курсов валют"""
    engine = message.bot.get("db_engine")
    
    currencies = await get_all_currencies(engine)
    
    text = "📊 <b>Актуальні курси обміну:</b>\n\n"
    
    # Получаем курсы для основных пар
    pairs = [
        ("USDT", "USD"), ("USD", "USDT"),
        ("USDT", "UAH"), ("UAH", "USDT")
    ]
    
    for from_curr, to_curr in pairs:
        rate = await get_exchange_rate(engine, from_curr, to_curr)
        if rate:
            text += f"• {from_curr} → {to_curr}: <b>{rate:.2f}</b>\n"
    
    text += "\nДля обміну використовуйте кнопку '🔄 Обмін валют'"
    
    await message.answer(text, parse_mode="HTML")

async def process_help_button(message: types.Message):
    """Обработчик кнопки Поддержка"""
    await message.answer(
        "🆘 <b>Підтримка</b>\n\n"
        "Якщо у вас виникли питання щодо роботи сервісу, будь ласка, зв'яжіться з нашим менеджером.\n\n"
        "Для зв'язку натисніть кнопку нижче.",
        reply_markup=get_support_keyboard()
    )

def get_support_keyboard():
    """Создает клавиатуру для связи с менеджером"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✉️ Написати менеджеру", callback_data="support:message"))
    
    return builder.as_markup()

def setup(dp: Dispatcher):
    """Регистрация обработчиков"""
    dp.message.register(process_rates_command, Text(text="📊 Курси валют"))
    dp.message.register(process_help_button, Text(text="🆘 Підтримка"))