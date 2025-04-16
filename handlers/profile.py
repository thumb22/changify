from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from database import db_session
from database.models import User, Order
from keyboards import get_profile_keyboard, get_main_keyboard
from utils import user_required

# Состояния для ConversationHandler
PROFILE_MAIN, EDITING_CONTACT = range(2)

@user_required
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отображает профиль пользователя и историю заявок"""
    user_id = update.effective_user.id
    
    with db_session() as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("Пользователь не найден. Пожалуйста, начните сначала с /start")
            return ConversationHandler.END
        
        # Получаем историю заявок
        orders = session.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(5).all()
        
        # Формируем текст профиля
        profile_text = f"📋 <b>Ваш профіль</b>\n\n"
        profile_text += f"👤 <b>Ім'я:</b> {update.effective_user.first_name}\n"
        profile_text += f"🆔 <b>Telegram ID:</b> {user_id}\n"
        
        if user.contact_info:
            profile_text += f"📞 <b>Контактна інформація:</b> {user.contact_info}\n"
        else:
            profile_text += "📞 <b>Контактна інформація:</b> Не вказана\n"
        
        profile_text += "\n<b>Останні заявки:</b>\n"
        
        if not orders:
            profile_text += "У вас ще немає заявок.\n"
        else:
            for i, order in enumerate(orders, 1):
                profile_text += f"{i}. {order.currency_from} → {order.currency_to} ({order.amount_from} {order.currency_from})\n"
                profile_text += f"   Статус: {order.status}, Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        
        keyboard = get_profile_keyboard()
        
        await update.message.reply_text(
            profile_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        return PROFILE_MAIN

async def edit_contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос на редактирование контактной информации"""
    await update.message.reply_text(
        "Будь ласка, введіть вашу контактну інформацію (номер телефону або інший контакт):",
        reply_markup=ReplyKeyboardMarkup([["Скасувати"]], resize_keyboard=True)
    )
    return EDITING_CONTACT

async def save_contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение новой контактной информации"""
    new_contact = update.message.text
    user_id = update.effective_user.id
    
    if new_contact == "Скасувати":
        await update.message.reply_text(
            "Редагування контактної інформації скасовано.",
            reply_markup=get_profile_keyboard()
        )
        return PROFILE_MAIN
    
    with db_session() as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        user.contact_info = new_contact
        session.commit()
    
    await update.message.reply_text(
        "✅ Ваша контактна інформація успішно оновлена!",
        reply_markup=get_profile_keyboard()
    )
    
    return PROFILE_MAIN

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в главное меню"""
    await update.message.reply_text(
        "Повертаємось до головного меню",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    return ConversationHandler.END

def get_profile_handlers():
    """Возвращает обработчики для профиля пользователя"""
    profile_conv = ConversationHandler(
        entry_points=[CommandHandler('profile', profile_command),
                      MessageHandler(filters.Regex('^(Профіль|👤 Профіль)$'), profile_command)],
        states={
            PROFILE_MAIN: [
                MessageHandler(filters.Regex('^(Редагувати контактну інформацію|✏️ Контакт)$'), edit_contact_info),
                MessageHandler(filters.Regex('^(Назад|🔙 Назад)$'), back_to_main),
            ],
            EDITING_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_contact_info),
            ],
        },
        fallbacks=[CommandHandler('cancel', back_to_main)],
    )
    
    return [profile_conv]