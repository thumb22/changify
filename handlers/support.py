from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.reply import get_main_keyboard, get_support_keyboard
from states.support import SupportStates
from utils.error_handler import handle_errors
import config

router = Router()

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
async def process_support_message(message: types.Message, state: FSMContext):
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

    manager_notification = (
        f"🆘 <b>Новий запит підтримки</b>\n\n"
        f"Від: {message.from_user.first_name} (@{username}, ID: {user_id})\n"
        f"Повідомлення: {message_text}\n\n"
        f"Для відповіді використовуйте команду /reply {user_id} [ваша відповідь]"
    )

    # Отправка уведомления менеджерам
    for manager_id in config.MANAGER_IDS:
        try:
            await message.bot.send_message(
                chat_id=manager_id,
                text=manager_notification,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Failed to send message to manager {manager_id}: {e}")

    await message.answer(
        "✅ Ваш запит успішно відправлено менеджеру!\n"
        "Ми зв'яжемося з вами якнайшвидше.",
        reply_markup=get_main_keyboard()
    )
    await state.set_state(SupportStates.MAIN)

@router.message(F.text == "🔙 Назад", SupportStates.MAIN)
@handle_errors
async def back_to_main(message: types.Message, state: FSMContext):
    await message.answer(
        "Повертаємось до головного меню",
        reply_markup=get_main_keyboard()
    ) 
    await state.clear()

def setup(dp):
    dp.include_router(router)