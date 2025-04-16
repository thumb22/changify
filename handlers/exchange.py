# handlers/exchange.py
from aiogram import Dispatcher, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from states.exchange import ExchangeStates
from keyboards.inline import get_currencies_selection, get_bank_selection
from utils.error_handler import handle_errors
from utils.db_utils import get_exchange_rate, get_banks_for_currency
from database.models import Currency, Order, OrderStatus

async def start_exchange(message: types.Message, state: FSMContext):
    """Начало процесса обмена"""
    await state.clear()
    await message.answer(
        "🔄 <b>Обмін валют</b>\n\n"
        "Оберіть валюту, яку хочете обміняти:",
        reply_markup=get_currencies_selection("from")
    )
    await state.set_state(ExchangeStates.SELECT_FROM_CURRENCY)

async def process_from_currency(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора исходной валюты"""
    await callback.answer()
    
    # Получаем код валюты из callback_data
    currency_code = callback.data.split(":")[2]
    
    # Сохраняем в состояние
    await state.update_data(from_currency=currency_code)
    
    # Предлагаем выбрать целевую валюту
    await callback.message.edit_text(
        f"Обрано: <b>{currency_code}</b>\n\n"
        f"Тепер оберіть валюту, на яку хочете обміняти:",
        reply_markup=get_currencies_selection("to", currency_code)
    )
    
    await state.set_state(ExchangeStates.SELECT_TO_CURRENCY)

async def process_to_currency(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора целевой валюты"""
    await callback.answer()
    
    # Получаем код валюты из callback_data
    currency_code = callback.data.split(":")[2]
    
    # Получаем данные из состояния
    data = await state.get_data()
    from_currency = data.get('from_currency')
    
    # Сохраняем в состояние
    await state.update_data(to_currency=currency_code)
    
    # Получаем текущий курс обмена
    engine = callback.bot.get("db_engine")
    rate = await get_exchange_rate(engine, from_currency, currency_code)
    
    if rate:
        await state.update_data(rate=rate)
        
        await callback.message.edit_text(
            f"Обмін: <b>{from_currency} → {currency_code}</b>\n"
            f"Поточний курс: <b>1 {from_currency} = {rate:.2f} {currency_code}</b>\n\n"
            f"Введіть суму {from_currency}, яку хочете обміняти:"
        )
        
        await state.set_state(ExchangeStates.ENTER_AMOUNT)
    else:
        await callback.message.edit_text(
            "На жаль, обмін для цієї пари валют тимчасово недоступний.\n"
            "Спробуйте вибрати іншу пару або зв'яжіться з підтримкою."
        )
        await state.clear()

async def process_amount(message: types.Message, state: FSMContext):
    """Обработка ввода суммы для обмена"""
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("Сума має бути більше нуля. Спробуйте ще раз:")
            return
    except ValueError:
        await message.answer("Будь ласка, введіть коректну суму числом. Спробуйте ще раз:")
        return
    
    # Сохраняем сумму в состояние
    await state.update_data(amount_from=amount)
    
    # Получаем данные из состояния
    data = await state.get_data()
    from_currency = data.get('from_currency')
    to_currency = data.get('to_currency')
    rate = data.get('rate')
    
    # Рассчитываем сумму к получению
    amount_to = amount * rate
    await state.update_data(amount_to=amount_to)
    
    # Проверяем, нужно ли выбирать банк (для UAH)
    engine = message.bot.get("db_engine")
    
    if to_currency == "UAH":
        # Если обмен на UAH, нужно выбрать банк
        await message.answer(
            f"Сума до обміну: <b>{amount:.2f} {from_currency}</b>\n"
            f"Сума до отримання: <b>{amount_to:.2f} {to_currency}</b>\n\n"
            f"Оберіть банк для отримання коштів:",
            reply_markup=get_bank_selection()
        )
        await state.set_state(ExchangeStates.SELECT_BANK)
    else:
        # Если не нужно выбирать банк, переходим к вводу реквизитов
        await message.answer(
            f"Сума до обміну: <b>{amount:.2f} {from_currency}</b>\n"
            f"Сума до отримання: <b>{amount_to:.2f} {to_currency}</b>\n\n"
            f"Введіть реквізити для отримання {to_currency}:"
        )
        await state.set_state(ExchangeStates.ENTER_PAYMENT_DETAILS)

async def process_bank_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора банка"""
    await callback.answer()
    
    # Получаем ID банка из callback_data
    bank_id = int(callback.data.split(":")[1])
    
    # Сохраняем в состояние
    await state.update_data(bank_id=bank_id)
    
    # Получаем данные из состояния
    data = await state.get_data()
    to_currency = data.get('to_currency')
    
    await callback.message.edit_text(
        f"Обрано банк: <b>{get_bank_name(bank_id)}</b>\n\n"
        f"Введіть реквізити (номер картки) для отримання {to_currency}:"
    )
    
    await state.set_state(ExchangeStates.ENTER_PAYMENT_DETAILS)

def get_bank_name(bank_id):
    """Получает название банка по ID"""
    # Здесь должна быть логика получения названия банка из БД
    banks = {1: "ПриватБанк", 2: "Монобанк", 3: "ПУМБ"}
    return banks.get(bank_id, "Невідомий банк")

async def process_payment_details(message: types.Message, state: FSMContext):
    """Обработка ввода реквизитов"""
    payment_details = message.text.strip()
    
    if len(payment_details) < 5:  # Минимальная валидация
        await message.answer("Реквізити занадто короткі. Будь ласка, введіть коректні дані:")
        return
    
    # Сохраняем в состояние
    await state.update_data(payment_details=payment_details)
    
    # Получаем все данные из состояния
    data = await state.get_data()
    from_currency = data.get('from_currency')
    to_currency = data.get('to_currency')
    amount_from = data.get('amount_from')
    amount_to = data.get('amount_to')
    bank_id = data.get('bank_id')
    
    # Формируем сообщение для подтверждения
    confirmation_text = (
        f"📝 <b>Підтвердження заявки на обмін</b>\n\n"
        f"Напрямок: <b>{from_currency} → {to_currency}</b>\n"
        f"Сума обміну: <b>{amount_from:.2f} {from_currency}</b>\n"
        f"Сума до отримання: <b>{amount_to:.2f} {to_currency}</b>\n"
    )
    
    if bank_id:
        confirmation_text += f"Банк: <b>{get_bank_name(bank_id)}</b>\n"
    
    confirmation_text += (
        f"Реквізити: <code>{payment_details}</code>\n\n"
        f"Перевірте дані та підтвердіть заявку:"
    )
    
    # Создаем клавиатуру для подтверждения
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Підтвердити", callback_data="order:confirm"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="order:cancel")
    )
    
    await message.answer(confirmation_text, reply_markup=builder.as_markup())
    await state.set_state(ExchangeStates.CONFIRM_ORDER)

async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение заявки"""
    await callback.answer()
    
    # Получаем данные из состояния
    data = await state.get_data()
    
    # Создаем заявку в БД
    engine = callback.bot.get("db_engine")
    # Здесь должен быть код для создания заявки

    await callback.message.edit_text(
        "✅ <b>Заявку створено!</b>\n\n"
        "Наш менеджер скоро зв'яжеться з вами для підтвердження деталей.\n"
        "Статус заявки можна перевірити в розділі '📋 Історія'."
    )
    
    # Уведомляем менеджеров о новой заявке
    # Здесь должен быть код отправки уведомления менеджерам
    
    await state.clear()

async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    """Отмена заявки"""
    await callback.answer()
    
    await callback.message.edit_text(
        "❌ Заявку скасовано.\n\n"
        "Ви можете створити нову заявку в будь-який час через меню '🔄 Обмін валют'."
    )
    
    await state.clear()

async def process_back_to_currencies(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки Назад при выборе валюты"""
    await callback.answer()
    
    current_state = await state.get_state()
    
    if current_state == ExchangeStates.SELECT_TO_CURRENCY:
        # Возвращаемся к выбору исходной валюты
        await callback.message.edit_text(
            "🔄 <b>Обмін валют</b>\n\n"
            "Оберіть валюту, яку хочете обміняти:",
            reply_markup=get_currencies_selection("from")
        )
        await state.set_state(ExchangeStates.SELECT_FROM_CURRENCY)
    else:
        # В других случаях просто сбрасываем состояние
        await callback.message.edit_text(
            "Операцію скасовано.\n\n"
            "Ви можете створити нову заявку в будь-який час через меню '🔄 Обмін валют'."
        )
        await state.clear()

def setup(dp: Dispatcher):
    """Регистрация обработчиков"""
    # Команды меню
    dp.message.register(start_exchange, Text(text="🔄 Обмін валют"))
    
    # Обработчики процесса создания заявки
    dp.callback_query.register(process_from_currency, 
                               lambda c: c.data.startswith("currency:from:"), 
                               ExchangeStates.SELECT_FROM_CURRENCY)
    
    dp.callback_query.register(process_to_currency, 
                               lambda c: c.data.startswith("currency:to:"), 
                               ExchangeStates.SELECT_TO_CURRENCY)
    
    dp.message.register(process_amount, ExchangeStates.ENTER_AMOUNT)
    
    dp.callback_query.register(process_bank_selection, 
                              lambda c: c.data.startswith("bank:") and not c.data.endswith(":back"), 
                              ExchangeStates.SELECT_BANK)
    
    dp.message.register(process_payment_details, ExchangeStates.ENTER_PAYMENT_DETAILS)
    
    dp.callback_query.register(confirm_order, 
                              lambda c: c.data == "order:confirm", 
                              ExchangeStates.CONFIRM_ORDER)
    
    dp.callback_query.register(cancel_order, 
                              lambda c: c.data == "order:cancel", 
                              ExchangeStates.CONFIRM_ORDER)
    
    # Обработчики кнопок "Назад"
    dp.callback_query.register(process_back_to_currencies, 
                              lambda c: c.data == "currency:back")
    
    dp.callback_query.register(process_back_to_currencies, 
                              lambda c: c.data == "bank:back", 
                              ExchangeStates.SELECT_BANK)