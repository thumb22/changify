from datetime import datetime
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards.reply import get_main_keyboard
from states.profile import ProfileStates
from utils.error_handler import handle_errors

router = Router()

@router.message(F.text == "👤 Профіль")
@handle_errors
async def cmd_profile(message: types.Message, db_user: dict, session):
    """Handler for profile command"""
    from database.models import Order
    from sqlalchemy.orm import Session
    from keyboards.inline import get_profile_settings
    
    orders = session.query(Order).filter(Order.user_id == db_user['telegram_id']).order_by(Order.created_at.desc()).limit(5).all()
    
    profile_text = f"📋 <b>Ваш профіль</b>\n\n"
    profile_text += f"👤 <b>Ім'я:</b> {message.from_user.first_name}\n"
    profile_text += f"🆔 <b>Telegram ID:</b> {message.from_user.id}\n"
    
    if message.from_user.username:
        profile_text += f"👤 <b>Username:</b> @{message.from_user.username}\n"
        
    created_at = db_user.get("created_at")
    if created_at:
        profile_text += f"📅 <b>Дата реєстрації:</b> {created_at.strftime('%d.%m.%Y %H:%M')}\n"
    else:
        profile_text += "📅 <b>Дата реєстрації:</b> Невідомо\n"

    
    profile_text += "\n<b>Останні заявки:</b>\n"
    
    if not orders:
        profile_text += "У вас ще немає заявок.\n"
    else:
        for i, order in enumerate(orders, 1):
            from_curr = order.from_currency.code
            to_curr = order.to_currency.code
            profile_text += f"{i}. {from_curr} → {to_curr} ({order.amount_from} {from_curr})\n"
            profile_text += f"   Статус: {order.status.value}, Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    await message.answer(
        profile_text,
        parse_mode="HTML",
        reply_markup=get_profile_settings()
    )


@router.callback_query(F.data == "profile:contacts")
@handle_errors
async def edit_contacts(callback: types.CallbackQuery, state: FSMContext):
    """Handler for editing contact information"""
    await state.set_state(ProfileStates.EDIT_CONTACTS)
    await callback.message.answer(
        "Будь ласка, введіть вашу контактну інформацію (номер телефону або інший контакт).\n"
        "Щоб скасувати, надішліть команду /cancel"
    )
    await callback.answer()


@router.message(ProfileStates.EDIT_CONTACTS)
@handle_errors
async def save_contacts(message: types.Message, state: FSMContext, db_user: dict, session):
    """Handler for saving contact information"""
    from sqlalchemy.orm import Session
    from database.models import User
    
    new_contact = message.text
    
    if new_contact == "/cancel":
        await state.clear()
        await message.answer("Редагування контактної інформації скасовано.")
        return
    

    user = session.query(User).filter(User.id == db_user['telegram_id']).first()
    if user:
        user.contact_info = new_contact
        session.commit()
    
    await state.clear()
    await message.answer(
        "✅ Ваша контактна інформація успішно оновлена!",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("cancel"))
@handle_errors
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Handler for cancel command - resets any state"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            "Дія скасована.",
            reply_markup=get_main_keyboard()
        )

def setup(dp):
    dp.include_router(router)