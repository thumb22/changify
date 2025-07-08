from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Tuple

from config import MANAGER_IDS
from keyboards.inline import get_order_actions
from keyboards.reply import get_main_keyboard, get_manager_keyboard
from states.manager import ManagerStates
from utils.error_handler import handle_errors
from database.models import ORDER_STATUS_LABELS, Order, OrderStatus, User, UserRole, Currency, Bank, ExchangeRate
import logging

router = Router()
logger = logging.getLogger(__name__)

# Helper function to check if user is manager or admin
def is_authorized(user_role):
    return user_role in [UserRole.MANAGER, UserRole.ADMIN]

def get_order_related_data(order, session) -> Tuple[Optional[User], Optional[Currency], Optional[Currency], Optional[Bank]]:
    user = session.query(User).filter_by(telegram_id=order.user_id).first()
    from_currency = session.query(Currency).filter_by(id=order.from_currency_id).first()
    to_currency = session.query(Currency).filter_by(id=order.to_currency_id).first()
    bank = session.query(Bank).filter_by(id=order.bank_id).first() if order.bank_id else None
    return user, from_currency, to_currency, bank

def format_order_text(order, user, from_currency, to_currency, bank) -> str:
    status_emoji = {
        OrderStatus.CREATED: "🆕",
        OrderStatus.AWAITING_PAYMENT: "⏳",
        OrderStatus.PAYMENT_CONFIRMED: "✅",
        OrderStatus.COMPLETED: "✅",
        OrderStatus.CANCELLED: "❌",
    }.get(order.status, "❓")

    text = (
        f"{status_emoji} <b>Заявка #{order.id}</b>\n\n"
        f"Користувач: {user.first_name or ''} {user.last_name or ''} "
        f"(@{user.username or 'немає'}, ID: {user.telegram_id})\n"
        f"Обмін: {order.amount_from} {from_currency.code} → {order.amount_to:.2f} {to_currency.code}\n"
        f"Курс: 1 {from_currency.code} = {order.rate:.2f} {to_currency.code}\n"
    )
    if bank:
        text += f"Банк: {bank.name}\n"

    text += (
        f"Реквізити клієнта: <code>{order.details}</code>\n"
    )
    if order.manager_payment_details:
        text += f"Платіжні реквізити менеджера: <code>{order.manager_payment_details}</code>\n"

    text += (
        f"Дата створення: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Статус: {ORDER_STATUS_LABELS[order.status]}\n"
    )
    return text

async def notify_user(bot, telegram_id: int, text: str, reply_markup=None):
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to send notification to user {telegram_id}: {e}")

def get_order_or_respond(callback: types.CallbackQuery, session, order_id: int):
    order = session.query(Order).filter_by(id=order_id).first()
    if not order:
        return None, callback.answer("Заявка не знайдена")
    return order, None

@router.message(F.text == "📝 Заявки")
@handle_errors
async def cmd_orders(message: types.Message, db_user: dict, session):
    if not is_authorized(db_user['role']):
        await message.answer("Доступ заборонено. Ця функція доступна тільки для менеджерів.")
        return
    
    active_statuses = [
        OrderStatus.CREATED, 
        OrderStatus.AWAITING_PAYMENT, 
        OrderStatus.PAYMENT_CONFIRMED
    ]
    
    orders = session.query(Order).filter(
        Order.status.in_(active_statuses)
    ).order_by(Order.created_at).all()
    
    if not orders:
        await message.answer("Немає активних заявок на даний момент.")
        return
    
    for order in orders:
        user, from_currency, to_currency, bank = get_order_related_data(order, session)
        if not user or not from_currency or not to_currency:
            logger.warning(f"Пропущено заявку #{order.id} через відсутні дані.")
            continue
        
        order_text = format_order_text(order, user, from_currency, to_currency, bank)
        builder = InlineKeyboardBuilder()
        
        if order.status == OrderStatus.CREATED:
            builder.row(
                types.InlineKeyboardButton(
                    text="✅ Прийняти",
                    callback_data=f"manager:accept:{order.id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Відхилити",
                    callback_data=f"manager:reject:{order.id}"
                )
            )
        elif order.status == OrderStatus.AWAITING_PAYMENT:
            builder.row(
                types.InlineKeyboardButton(
                    text="💰 Підтвердити оплату",
                    callback_data=f"manager:confirm_payment:{order.id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Відхилити",
                    callback_data=f"manager:reject:{order.id}"
                )
            )
        elif order.status == OrderStatus.PAYMENT_CONFIRMED:
            builder.row(
                types.InlineKeyboardButton(
                    text="✅ Завершити",
                    callback_data=f"manager:complete:{order.id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Відхилити",
                    callback_data=f"manager:reject:{order.id}"
                )
            )
        
        order_message = await message.answer(order_text, reply_markup=builder.as_markup())
        order.message_id = order_message.message_id
        session.commit()

@router.callback_query(F.data.startswith("manager:accept:"))
@handle_errors
async def accept_order(callback: types.CallbackQuery, db_user: dict, session, state: FSMContext):
    """Accept an order and prompt for payment details"""
    if not is_authorized(db_user['role']):
        await callback.answer("Доступ заборонено")
        return
    
    order_id = int(callback.data.split(":")[2])
    order = session.query(Order).filter_by(id=order_id).first()
    
    if not order:
        await callback.answer("Заявка не знайдена")
        return
    
    if order.status != OrderStatus.CREATED:
        await callback.answer(f"Заявка в неправильному статусі: {order.status.value}")
        return
    
    # Update order status and assign manager
    order.status = OrderStatus.AWAITING_PAYMENT
    order.manager_id = db_user['telegram_id']
    order.updated_at = datetime.now(ZoneInfo("Europe/Kyiv"))
    session.commit()
    
    # Сохраняем order_id в FSM для последующей обработки
    await state.update_data(order_id=order_id)
    await state.set_state(ManagerStates.awaiting_payment_details)
    
    # Запрашиваем у менеджера реквизиты
    await callback.message.answer(
        "Будь ласка, введіть платіжні реквізити для цієї заявки:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="🔙 Скасувати введення реквізитів")]],
            resize_keyboard=True
        )
    )
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n⏳ Очікується введення платіжних реквізитів.",
        reply_markup=None
    )
    
    await callback.answer("Введіть реквізити")

@router.callback_query(F.data.startswith("manager:confirm_payment:"))
@handle_errors
async def confirm_payment(callback: types.CallbackQuery, db_user: dict, session):
    """Confirm payment received for an order"""
    if not is_authorized(db_user['role']):
        await callback.answer("Доступ заборонено")
        return
    
    order_id = int(callback.data.split(":")[2])
    order = session.query(Order).filter_by(id=order_id).first()
    
    if not order:
        await callback.answer("Заявка не знайдена")
        return
    
    if order.status != OrderStatus.AWAITING_PAYMENT:
        await callback.answer(f"Заявка в неправильному статусі: {order.status.value}")
        return
    
    # Update order status
    order.status = OrderStatus.PAYMENT_CONFIRMED
    order.updated_at = datetime.now(ZoneInfo("Europe/Kyiv"))
    session.commit()
    
    # Notify customer
    user = session.query(User).filter_by(telegram_id=order.user_id).first()
    to_currency = session.query(Currency).filter_by(id=order.to_currency_id).first()
    
    customer_notification = (
        f"✅ <b>Оплату для заявки #{order.id} підтверджено!</b>\n\n"
        f"Ми обробляємо ваш обмін і скоро відправимо {order.amount_to:.2f} {to_currency.code} "
        f"на вказані вами реквізити."
    )
    
    try:
        await callback.bot.send_message(
            chat_id=user.telegram_id,
            text=customer_notification,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send notification to user {user.telegram_id}: {e}")
    
    # Update the callback message
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ Оплату підтверджено. Клієнта повідомлено.",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(
                text="✅ Завершити",
                callback_data=f"manager:complete:{order.id}"
            )
        ).as_markup()
    )
    
    await callback.answer("Оплату підтверджено")

@router.callback_query(F.data.startswith("manager:complete:"))
@handle_errors
async def complete_order(callback: types.CallbackQuery, db_user: dict, session):
    """Complete an order after sending funds to the customer"""
    if not is_authorized(db_user['role']):
        await callback.answer("Доступ заборонено")
        return
    
    order_id = int(callback.data.split(":")[2])
    order = session.query(Order).filter_by(id=order_id).first()
    
    if not order:
        await callback.answer("Заявка не знайдена")
        return
    
    if order.status != OrderStatus.PAYMENT_CONFIRMED:
        await callback.answer(f"Заявка в неправильному статусі: {order.status.value}")
        return
    
    # Update order status
    order.status = OrderStatus.COMPLETED
    order.updated_at = datetime.now(ZoneInfo("Europe/Kyiv"))
    order.completed_at = datetime.now(ZoneInfo("Europe/Kyiv"))
    session.commit()
    
    # Notify customer
    user = session.query(User).filter_by(telegram_id=order.user_id).first()
    to_currency = session.query(Currency).filter_by(id=order.to_currency_id).first()
    
    customer_notification = (
        f"✅ <b>Заявку #{order.id} завершено!</b>\n\n"
        f"Ми відправили {order.amount_to:.2f} {to_currency.code} на вказані вами реквізити.\n\n"
        f"Дякуємо за використання нашого сервісу! Будемо раді бачити вас знову."
    )
    
    try:
        await callback.bot.send_message(
            chat_id=user.telegram_id,
            text=customer_notification,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send notification to user {user.telegram_id}: {e}")
    
    # Update the callback message
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ Заявку завершено. Клієнта повідомлено.",
        reply_markup=None
    )
    
    await callback.answer("Заявку завершено")

@router.callback_query(F.data.startswith("manager:reject:"))
@handle_errors
async def reject_order(callback: types.CallbackQuery, db_user: dict, session, state: FSMContext):
    """Initiate rejection of an order and prompt for a comment"""
    if not is_authorized(db_user['role']):
        await callback.answer("Доступ заборонено")
        return
    
    order_id = int(callback.data.split(":")[2])
    order = session.query(Order).filter_by(id=order_id).first()
    
    if not order:
        await callback.answer("Заявка не знайдена")
        return
    
    if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
        await callback.answer(f"Заявка вже в кінцевому статусі: {order.status.value}")
        return
    
    await state.update_data(order_id=order_id)
    await state.set_state(ManagerStates.awaiting_rejection_comment)
    
    await callback.message.answer(
        "Будь ласка, вкажіть причину відхилення заявки:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="🔙 Скасувати відхилення")]],
            resize_keyboard=True
        )
    )
    
    await callback.answer()

@router.message(ManagerStates.awaiting_rejection_comment)
@handle_errors
async def process_rejection_comment(message: types.Message, db_user: dict, session, state: FSMContext):
    """Process the rejection comment and finalize order cancellation"""
    if not is_authorized(db_user['role']):
        await message.answer("Доступ заборонено.")
        return
    
    # Get order_id from FSM context
    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await message.answer("Помилка: ID заявки не знайдено.")
        await state.clear()
        return
    
    order = session.query(Order).filter_by(id=order_id).first()
    if not order:
        await message.answer("Заявка не знайдена.")
        await state.clear()
        return
    
    if message.text == "🔙 Скасувати відхилення":
        await message.answer("Відхилення заявки скасовано.", reply_markup=get_manager_keyboard())
        await state.clear()
        return
    
    # Store the rejection comment
    rejection_reason = message.text
    order.rejection_reason = rejection_reason
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now(ZoneInfo("Europe/Kyiv"))
    session.commit()
    
    # Notify customer
    user = session.query(User).filter_by(telegram_id=order.user_id).first()
    
    customer_notification = (
        f"❌ <b>Заявку #{order.id} скасовано</b>\n\n"
        f"Причина: {rejection_reason}\n\n"
        f"Якщо у вас виникли питання, зверніться до підтримки через меню 'Підтримка'."
    )
    
    try:
        await message.bot.send_message(
            chat_id=user.telegram_id,
            text=customer_notification,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send notification to user {user.telegram_id}: {e}")
    
    # Update the original order message
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=order.message_id if hasattr(order, 'message_id') else message.message_id,
            text=f"{format_order_text(order, user, *get_order_related_data(order, session)[1:])}\n\n❌ Заявку скасовано. Причина: {rejection_reason}",
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Failed to edit original message for order {order.id}: {e}")
    
    await message.answer(
        f"✅ Заявку #{order.id} скасовано. Клієнта повідомлено.",
        reply_markup=get_manager_keyboard()
    )
    
    # Clear FSM state
    await state.clear()

@router.message(F.text == "✅ Завершені")
@handle_errors
async def cmd_completed_orders(message: types.Message, db_user: dict, session):
    """Show completed orders"""
    if not is_authorized(db_user['role']):
        await message.answer("Доступ заборонено. Ця функція доступна тільки для менеджерів.")
        return
    
    # Get completed orders
    completed_orders = session.query(Order).filter(
        Order.status == OrderStatus.COMPLETED
    ).order_by(Order.completed_at.desc()).limit(10).all()
    
    if not completed_orders:
        await message.answer("Немає завершених заявок.")
        return
    
    text = "✅ <b>Останні завершені заявки:</b>\n\n"
    
    for order in completed_orders:
        user = session.query(User).filter_by(telegram_id=order.user_id).first()
        from_currency = session.query(Currency).filter_by(id=order.from_currency_id).first()
        to_currency = session.query(Currency).filter_by(id=order.to_currency_id).first()
        
        text += (
            f"<b>Заявка #{order.id}</b> ({order.completed_at.strftime('%d.%m.%Y %H:%M')})\n"
            f"Користувач: {user.first_name or ''} (@{user.username or 'немає'})\n"
            f"Обмін: {order.amount_from} {from_currency.code} → {order.amount_to:.2f} {to_currency.code}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")

@router.message(Command("reply"))
@handle_errors
async def cmd_reply_to_user(message: types.Message, db_user: dict, session):
    """Reply to user support message"""
    if not is_authorized(db_user['role']):
        await message.answer("Доступ заборонено. Ця функція доступна тільки для менеджерів.")
        return
    
    # Parse command: /reply user_id message
    command_parts = message.text.split(maxsplit=2)
    if len(command_parts) < 3:
        await message.answer("Використання: /reply USER_ID ТЕКСТ_ПОВІДОМЛЕННЯ")
        return
    
    try:
        user_id = int(command_parts[1])
        reply_text = command_parts[2]
    except ValueError:
        await message.answer("Неправильний формат ID користувача. Використання: /reply USER_ID ТЕКСТ_ПОВІДОМЛЕННЯ")
        return
    
    # Check if user exists
    user = session.query(User).filter_by(telegram_id=user_id).first()
    if not user:
        await message.answer(f"Користувач з ID {user_id} не знайдений.")
        return
    
    # Send reply to user - with information about continuing the conversation
    try:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🔙 Завершити чат з підтримкою")]
            ],
            resize_keyboard=True
        )
        
        await message.bot.send_message(
            chat_id=user_id,
            text=f"📬 <b>Відповідь від підтримки:</b>\n\n{reply_text}\n\n"
                 f"Ви можете продовжити діалог, просто надіславши повідомлення у відповідь.",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await message.answer(f"✅ Повідомлення успішDoppelgänger successfully sent the message to user {user_id}. "
                             f"Користувач може відповідати безпосередньо.")
        
    except Exception as e:
        await message.answer(f"❌ Помилка при відправці повідомлення: {e}")

@router.message(Command("close_chat"))
@handle_errors
async def cmd_close_chat(message: types.Message, db_user: dict, session):
    """Close an active support chat with a user"""
    if not is_authorized(db_user['role']):
        await message.answer("Доступ заборонено. Ця функція доступна тільки для менеджерів.")
        return
    
    # Parse command: /close_chat user_id [optional message]
    command_parts = message.text.split(maxsplit=2)
    if len(command_parts) < 2:
        await message.answer("Використання: /close_chat USER_ID [необов'язкове повідомлення]")
        return
    
    try:
        user_id = int(command_parts[1])
        optional_message = command_parts[2] if len(command_parts) > 2 else "Чат з підтримкою було завершено менеджером."
    except ValueError:
        await message.answer("Неправильний формат ID користувача. Використання: /close_chat USER_ID [необов'язкове повідомлення]")
        return
    
    # Check if user exists
    user = session.query(User).filter_by(telegram_id=user_id).first()
    if not user:
        await message.answer(f"Користувач з ID {user_id} не знайдений.")
        return
    
    # Send final message to user
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=f"📬 <b>Повідомлення від підтримки:</b>\n\n{optional_message}\n\n"
                 f"Чат з підтримкою завершено. Якщо у вас виникнуть нові питання, ви завжди можете звернутися до підтримки.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        
        # Notify other managers that this chat was closed
        manager_name = message.from_user.first_name or ""
        manager_username = message.from_user.username or "немає"
        user_first_name = user.first_name or ""
        user_username = user.username or "немає"
        
        chat_closed_notification = (
            f"🔔 <b>Повідомлення системи</b>\n\n"
            f"Менеджер {manager_name} (@{manager_username}) "
            f"завершив чат з користувачем {user_first_name} (@{user_username}, ID: {user_id})."
        )
        
        for manager_id in MANAGER_IDS:
            if manager_id != message.from_user.id:  # Don't send to the closing manager
                try:
                    await message.bot.send_message(
                        chat_id=manager_id,
                        text=chat_closed_notification,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Failed to send notification to manager {manager_id}: {e}")
        
        await message.answer(f"✅ Чат з користувачем {user_id} успішно завершено.")
        
    except Exception as e:
        await message.answer(f"❌ Помилка при закритті чату: {e}")

@router.message(ManagerStates.awaiting_payment_details)
@handle_errors
async def process_payment_details(message: types.Message, db_user: dict, session, state: FSMContext):
    """Process the payment details provided by the manager"""
    if not is_authorized(db_user['role']):
        await message.answer("Доступ заборонено.")
        return
    
    # Получаем order_id из FSM
    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await message.answer("Помилка: ID заявки не знайдено.")
        await state.clear()
        return
    
    order = session.query(Order).filter_by(id=order_id).first()
    if not order:
        await message.answer("Заявка не знайдена.")
        await state.clear()
        return
    
    if message.text == "🔙 Скасувати введення реквізитів":
        # Возвращаем заявку в статус CREATED и очищаем менеджера
        order.status = OrderStatus.CREATED
        order.manager_id = None
        session.commit()
        
        await message.answer(
            "Введення реквізитів скасовано. Заявка повернута до статусу 'Створена'.",
            reply_markup=get_manager_keyboard()
        )
        await state.clear()
        return
    
    # Сохраняем введенные реквизиты в новое поле
    manager_payment_details = message.text
    order.manager_payment_details = manager_payment_details
    session.commit()
    
    # Получаем данные для уведомления клиента
    user = session.query(User).filter_by(telegram_id=order.user_id).first()
    from_currency = session.query(Currency).filter_by(id=order.from_currency_id).first()
    
    customer_notification = (
        f"✅ <b>Заявку #{order.id} прийнято!</b>\n\n"
        f"Для продовження, будь ласка, відправте {order.amount_from} {from_currency.code} на наступні реквізити:\n\n"
        f"<code>{manager_payment_details}</code>\n\n"
        f"Після оплати натисніть кнопку 'Я оплатив' у деталях заявки."
    )
    
    try:
        await notify_user(
            bot=message.bot,
            telegram_id=user.telegram_id,
            text=customer_notification,
            reply_markup=get_order_actions(order.id, OrderStatus.AWAITING_PAYMENT.value)
        )
    except Exception as e:
        logger.error(f"Failed to send notification to user {user.telegram_id}: {e}")
    
    # Обновляем сообщение в чате менеджера
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=order.message_id if hasattr(order, 'message_id') else message.message_id,
            text=f"{format_order_text(order, user, *get_order_related_data(order, session)[1:])}\n\n✅ Заявку прийнято. Клієнту надіслано реквізити.",
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Failed to edit original message for order {order.id}: {e}")
    
    await message.answer(
        f"✅ Реквізити для заявки #{order.id} збережено та надіслано клієнту.",
        reply_markup=get_manager_keyboard()
    )
    
    # Очищаем состояние
    await state.clear()

def setup(dp):
    dp.include_router(router)