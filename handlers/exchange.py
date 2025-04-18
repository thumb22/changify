from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import MANAGER_IDS
from keyboards.reply import get_main_keyboard
from keyboards.inline import get_currencies_selection, get_bank_selection, get_order_actions
from states.exchange import ExchangeStates
from utils import logger
from utils.error_handler import handle_errors
from utils.db_utils import get_exchange_rate, get_banks_for_currency
from database.models import Order, OrderStatus, Currency, Bank, User

router = Router()

@router.callback_query(F.data.startswith("currency:"))
@handle_errors
async def process_currency_selection(callback: types.CallbackQuery, state: FSMContext, session):
    """Process currency selection callbacks"""
    parts = callback.data.split(":")
    action = parts[1]
    
    if action == "back":
        await state.clear()
        await callback.message.edit_text(
            "Операцію скасовано. Оберіть дію в меню.",
            reply_markup=None
        )
        await callback.answer()
        return
    
    current_state = await state.get_state()
    
    if action == "from":
        currency_code = parts[2]
        await state.update_data(from_currency=currency_code)
        await state.set_state(ExchangeStates.SELECT_TO_CURRENCY)
        
        await callback.message.edit_text(
            f"Обрана валюта: {currency_code}\n\nТепер оберіть валюту, яку хочете отримати:",
            reply_markup=get_currencies_selection("to", currency_code)
        )
    
    elif action == "to" and current_state == ExchangeStates.SELECT_TO_CURRENCY:
        currency_code = parts[2]
        data = await state.get_data()
        from_currency = data.get("from_currency")
        
        await state.update_data(to_currency=currency_code)
        
        rate = await get_exchange_rate(session, from_currency, currency_code)
        
        if rate:
            await state.update_data(rate=rate)
            await state.set_state(ExchangeStates.ENTER_AMOUNT)
            
            await callback.message.edit_text(
                f"Обмін {from_currency} → {currency_code}\n"
                f"Поточний курс: 1 {from_currency} = {rate:.2f} {currency_code}\n\n"
                f"Введіть суму {from_currency}, яку хочете обміняти:",
                reply_markup=None
            )
        else:
            await callback.message.edit_text(
                f"На жаль, обмін {from_currency} → {currency_code} тимчасово недоступний.\n"
                f"Спробуйте вибрати інші валюти.",
                reply_markup=get_currencies_selection("from")
            )
            await state.set_state(ExchangeStates.SELECT_FROM_CURRENCY)
    
    await callback.answer()


@router.message(ExchangeStates.ENTER_AMOUNT)
@handle_errors
async def process_amount(message: types.Message, state: FSMContext, session):
    """Process amount input"""
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await message.answer("Будь ласка, введіть коректну суму у вигляді числа (наприклад, 100 або 100.50).")
        return
    
    data = await state.get_data()
    from_currency = data.get("from_currency")
    to_currency = data.get("to_currency")
    rate = data.get("rate")
    
    amount_to = amount * rate
    
    await state.update_data(amount_from=amount, amount_to=amount_to)
    
    # Check if we need to select a bank (for fiat currencies)
    if to_currency == "UAH":
        banks = await get_banks_for_currency(session, to_currency)
        if banks:
            await state.set_state(ExchangeStates.SELECT_BANK)
            await message.answer(
                f"Ви хочете обміняти {amount} {from_currency} на {amount_to:.2f} {to_currency}.\n\n"
                f"Оберіть банк для отримання коштів:",
                reply_markup=get_bank_selection()
            )
            return
    
    # If no bank selection needed, go to payment details
    await state.set_state(ExchangeStates.ENTER_PAYMENT_DETAILS)
    await message.answer(
        f"Ви хочете обміняти {amount} {from_currency} на {amount_to:.2f} {to_currency}.\n\n"
        f"Введіть реквізити для отримання {to_currency}:"
    )


@router.callback_query(ExchangeStates.SELECT_BANK, F.data.startswith("bank:"))
@handle_errors
async def process_bank_selection(callback: types.CallbackQuery, state: FSMContext, session):
    """Process bank selection"""
    parts = callback.data.split(":")
    action = parts[1]
    
    if action == "back":
        await state.set_state(ExchangeStates.ENTER_AMOUNT)
        data = await state.get_data()
        from_currency = data.get("from_currency")
        to_currency = data.get("to_currency")
        rate = data.get("rate")
        
        await callback.message.edit_text(
            f"Обмін {from_currency} → {to_currency}\n"
            f"Поточний курс: 1 {from_currency} = {rate:.2f} {to_currency}\n\n"
            f"Введіть суму {from_currency}, яку хочете обміняти:",
            reply_markup=None
        )
        await callback.answer()
        return
    
    bank_id = int(parts[1])
    await state.update_data(bank_id=bank_id)
    
    bank = session.query(Bank).filter(Bank.id == bank_id).first()
    if bank:
        await state.update_data(bank_name=bank.name)
    
    data = await state.get_data()
    amount_from = data.get("amount_from")
    amount_to = data.get("amount_to")
    from_currency = data.get("from_currency")
    to_currency = data.get("to_currency")
    
    await state.set_state(ExchangeStates.ENTER_PAYMENT_DETAILS)
    await callback.message.edit_text(
        f"Ви хочете обміняти {amount_from} {from_currency} на {amount_to:.2f} {to_currency}.\n"
        f"Банк для отримання: {data.get('bank_name')}\n\n"
        f"Введіть номер картки або реквізити для отримання коштів:",
        reply_markup=None
    )
    await callback.answer()


@router.message(ExchangeStates.ENTER_PAYMENT_DETAILS)
@handle_errors
async def process_payment_details(message: types.Message, state: FSMContext, db_user: dict, session):
    """Process payment details and create order"""
    payment_details = message.text
    
    if len(payment_details) < 5:
        await message.answer("Будь ласка, введіть детальніші реквізити для отримання коштів.")
        return
    
    data = await state.get_data()
    from_currency = data.get("from_currency")
    to_currency = data.get("to_currency")
    amount_from = data.get("amount_from")
    amount_to = data.get("amount_to")
    rate = data.get("rate")
    bank_id = data.get("bank_id")
    
    # Get currency objects
    from_curr = session.query(Currency).filter(Currency.code == from_currency).first()
    to_curr = session.query(Currency).filter(Currency.code == to_currency).first()
    
    if not from_curr or not to_curr:
        await message.answer("Помилка при створенні заявки. Спробуйте пізніше.")
        await state.clear()
        return
    
    # Create new order
    new_order = Order(
        user_id=db_user['telegram_id'],
        from_currency_id=from_curr.id,
        to_currency_id=to_curr.id,
        amount_from=amount_from,
        amount_to=amount_to,
        rate=rate,
        status=OrderStatus.CREATED,
        bank_id=bank_id,
        details=payment_details
    )
    
    session.add(new_order)
    session.commit()
    order_id = new_order.id

    # Получаем объекты для уведомления менеджера
    user = session.query(User).filter(User.telegram_id == db_user['telegram_id']).first()
    bank = session.query(Bank).filter(Bank.id == bank_id).first() if bank_id else None

    # Формируем текст для менеджера
    manager_text = (
        f"🆕 <b>Нова заявка #{order_id}</b>\n\n"
        f"👤 Користувач: {user.first_name or ''} {user.last_name or ''} "
        f"(@{user.username or 'немає'}, ID: {user.telegram_id})\n"
        f"💱 Обмін: {amount_from} {from_currency} → {amount_to:.2f} {to_currency}\n"
        f"📊 Курс: 1 {from_currency} = {rate:.2f} {to_currency}\n"
    )
    if bank:
        manager_text += f"🏦 Банк: {bank.name}\n"

    manager_text += (
        f"📝 Реквізити: <code>{payment_details}</code>\n"
        f"📅 Дата: {new_order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"⏳ Статус: {new_order.status.value}"
    )

    for manager_id in MANAGER_IDS:
        try:
            await message.bot.send_message(
                chat_id=manager_id,
                text=manager_text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не вдалося надіслати заявку менеджеру {manager_id}: {e}")

        
    # Clear state and send confirmation
    await state.clear()
    
    # Send confirmation to user
    confirmation_text = (
        f"✅ <b>Заявка #{order_id} створена!</b>\n\n"
        f"💱 Обмін: {amount_from} {from_currency} → {amount_to:.2f} {to_currency}\n"
        f"📊 Курс: 1 {from_currency} = {rate:.2f} {to_currency}\n"
    )
    
    if bank_id:
        confirmation_text += f"🏦 Банк: {data.get('bank_name')}\n"
    
    confirmation_text += (
        f"📝 Реквізити: {payment_details}\n\n"
        f"Для завершення обміну вам потрібно буде відправити {amount_from} {from_currency} "
        f"на вказані реквізити після підтвердження заявки менеджером.\n\n"
        f"Статус заявки ви можете перевірити в розділі '📋 Історія'."
    )
    
    await message.answer(
        confirmation_text,
        parse_mode="HTML",
        reply_markup=get_order_actions(order_id, "created")
    )
    
def setup(dp):
    dp.include_router(router)