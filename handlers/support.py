from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
from database.models import User, SupportRequest
from keyboards.reply import get_main_keyboard, get_support_keyboard
# from utils import send_message_to_managers
from utils.error_handler import handle_errors

router = Router()

class SupportStates(StatesGroup):
    MAIN = State()
    SENDING_MESSAGE = State()

@router.message(F.text == "🆘 Підтримка")
@handle_errors
async def support_command(message: types.Message, state: FSMContext):
    await message.answer(
        "📞 <b>Зв'язок з менеджером</b>\n\n"
        "Ви можете задати питання або отримати допомогу від наших менеджерів.\n"
        "Виберіть опцію нижче:",
        reply_markup=get_support_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SupportStates.MAIN)

@router.message(F.text == "✉️ Новий запит", SupportStates.MAIN)
@handle_errors
async def start_new_request(message: types.Message, state: FSMContext):
    await message.answer(
        "Будь ласка, опишіть ваше питання або проблему. "
        "Менеджер зв'яжеться з вами якнайшвидше.",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Скасувати")]],
            resize_keyboard=True
        )
    )
    await state.set_state(SupportStates.SENDING_MESSAGE)

@router.message(SupportStates.SENDING_MESSAGE)
@handle_errors
async def process_support_message(message: types.Message, state: FSMContext, engine, db_user: dict):
    message_text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "Без імені користувача"

    if message_text == "Скасувати":
        await message.answer(
            "Запит скасовано.",
            reply_markup=get_support_keyboard()
        )
        await state.set_state(SupportStates.MAIN)
        return

    with Session(engine) as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await message.answer("Користувач не знайдений. Будь ласка, почніть з /start")
            await state.clear()
            return

        support_request = SupportRequest(
            user_id=user.id,
            message=message_text,
            status="pending"
        )
        session.add(support_request)
        session.commit()
        request_id = support_request.id

    manager_notification = (
        f"🆘 <b>Новий запит підтримки #{request_id}</b>\n\n"
        f"Від: {message.from_user.first_name} (@{username}, ID: {user_id})\n"
        f"Повідомлення: {message_text}\n\n"
        f"Для відповіді використовуйте команду /reply {request_id} [ваша відповідь]"
    )

    print(f"Would send to managers: {manager_notification}")    
    # await send_message_to_managers(message.bot, manager_notification)

    await message.answer(
        "✅ Ваш запит успішно відправлено менеджеру!\n"
        "Ми зв'яжемося з вами якнайшвидше.",
        reply_markup=get_support_keyboard()
    )
    await state.set_state(SupportStates.MAIN)

@router.message(F.text == "📋 Історія", SupportStates.MAIN)
@handle_errors
async def view_support_history(message: types.Message, engine, db_user: dict):
    user_id = message.from_user.id

    with Session(engine) as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await message.answer("Користувач не знайдений. Будь ласка, почніть з /start")
            return

        requests = session.query(SupportRequest).filter(
            SupportRequest.user_id == user.id
        ).order_by(SupportRequest.created_at.desc()).limit(5).all()

    if not requests:
        await message.answer(
            "У вас ще немає запитів у підтримку.",
            reply_markup=get_support_keyboard()
        )
        return

    history_text = "📋 <b>Історія ваших запитів:</b>\n\n"
    for req in requests:
        status_emoji = "⏳" if req.status == "pending" else "✅" if req.status == "answered" else "🔒"
        status_text = "В очікуванні" if req.status == "pending" else "Відповідь отримана" if req.status == "answered" else "Закрито"
        history_text += f"<b>Запит #{req.id}</b> {status_emoji} {status_text}\n"
        history_text += f"📅 {req.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        history_text += f"💬 {req.message[:50]}{'...' if len(req.message) > 50 else ''}\n"
        if req.answer:
            history_text += f"📝 <b>Відповідь:</b> {req.answer[:50]}{'...' if len(req.answer) > 50 else ''}\n"
        history_text += "\n"

    await message.answer(
        history_text,
        reply_markup=get_support_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "🔙 Назад", SupportStates.MAIN)
@handle_errors
async def back_to_main(message: types.Message, state: FSMContext):
    await message.answer(
        "Повертаємось до головного меню",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

def setup_support_handlers(dp):
    dp.include_router(router)