from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards.reply import get_main_keyboard
from keyboards.inline import get_currencies_selection, get_pagination_keyboard
from states.exchange import ExchangeStates
from utils.error_handler import handle_errors
from utils.db_utils import get_all_currencies, get_exchange_rate, get_banks_for_currency
from database.models import User, UserRole

router = Router()

@router.message(F.text == "🔄 Обмін валют")
@handle_errors
async def exchange_start(message: types.Message, state: FSMContext, db_user: dict):
    await state.set_state(ExchangeStates.SELECT_FROM_CURRENCY)
    await message.answer(
        "💱 <b>Обмін валют</b>\n\n"
        "Оберіть валюту, яку хочете обміняти:",
        reply_markup=get_currencies_selection("from")
    )

@router.message(F.text == "📊 Курси валют")
@handle_errors
async def show_rates(message: types.Message, db_user: dict, engine):
    currencies = await get_all_currencies(engine)
    if not currencies:
        await message.answer("На жаль, інформація про курси валют тимчасово недоступна.")
        return
    rates_text = "💹 <b>Поточні курси обміну</b>\n\n"
    pairs = [("USDT", "UAH"), ("USD", "UAH"), ("USDT", "USD")]
    for from_curr, to_curr in pairs:
        rate = await get_exchange_rate(engine, from_curr, to_curr)
        if rate:
            rates_text += f"<b>{from_curr} → {to_curr}:</b> {rate:.2f}\n"
    rates_text += "\nКурси можуть змінюватися. Для здійснення обміну натисніть '🔄 Обмін валют'"
    await message.answer(rates_text, parse_mode="HTML")

@router.message(F.text == "📋 Історія")
@handle_errors
async def show_history(message: types.Message, db_user: dict, engine):
    from sqlalchemy.orm import Session
    from database.models import Order, OrderStatus
    with Session(engine) as session:
        orders = session.query(Order).filter(Order.user_id == db_user['id']).order_by(Order.created_at.desc()).limit(5).all()
        if not orders:
            await message.answer("У вашій історії ще немає заявок на обмін.")
            return
        history_text = "📝 <b>Ваша історія заявок</b>\n\n"
        for order in orders:
            status_emoji = {
                OrderStatus.CREATED: "🆕",
                OrderStatus.AWAITING_PAYMENT: "⏳",
                OrderStatus.PAYMENT_CONFIRMED: "✅",
                OrderStatus.PROCESSING: "⚙️",
                OrderStatus.COMPLETED: "✅",
                OrderStatus.CANCELLED: "❌"
            }.get(order.status, "❓")
            history_text += (
                f"<b>Заявка #{order.id}</b> {status_emoji}\n"
                f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"💱 {order.amount_from} {order.from_currency.code} → "
                f"{order.amount_to} {order.to_currency.code}\n"
                f"📊 Курс: {order.rate:.2f}\n"
                f"📑 Статус: {order.status.value}\n\n"
            )
        await message.answer(
            history_text,
            parse_mode="HTML",
            reply_markup=get_pagination_keyboard(1, 1, "history")
        )

@router.message(F.text == "🆘 Підтримка")
@handle_errors
async def show_support(message: types.Message, db_user: dict):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✉️ Написати у підтримку", callback_data="support:new")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Історія звернень", callback_data="support:history")
    )
    await message.answer(
        "🆘 <b>Підтримка</b>\n\n"
        "Якщо у вас виникли питання або проблеми з використанням бота, "
        "ви можете зв'язатися з нашою підтримкою.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("support:"))
@handle_errors
async def process_support_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    if action == "new":
        await callback.message.answer(
            "✍️ Будь ласка, опишіть ваше питання або проблему в одному повідомленні."
        )
        await callback.answer()
    elif action == "history":
        await callback.message.answer(
            "📋 Історія ваших звернень буде тут.\n"
            "Поки що ця функція в розробці."
        )
        await callback.answer()

def setup_user_handlers(dp):
    dp.include_router(router)