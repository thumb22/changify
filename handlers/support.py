from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from database import db_session
from database.models import User, SupportRequest
from keyboards import get_main_keyboard, get_support_keyboard
from utils import user_required, send_message_to_managers

# Состояния для ConversationHandler
SUPPORT_MAIN, SENDING_MESSAGE = range(2)

@user_required
async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Открывает меню поддержки"""
    await update.message.reply_text(
        "📞 <b>Зв'язок з менеджером</b>\n\n"
        "Ви можете задати питання або отримати допомогу від наших менеджерів.\n"
        "Виберіть опцію нижче:",
        reply_markup=get_support_keyboard(),
        parse_mode="HTML"
    )
    return SUPPORT_MAIN

async def start_new_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс создания нового запроса в поддержку"""
    await update.message.reply_text(
        "Будь ласка, опишіть ваше питання або проблему. "
        "Менеджер зв'яжеться з вами якнайшвидше.",
        reply_markup=ReplyKeyboardMarkup([["Скасувати"]], resize_keyboard=True)
    )
    return SENDING_MESSAGE

async def process_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает сообщение пользователя и отправляет его менеджерам"""
    message_text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "Без імені користувача"
    
    if message_text == "Скасувати":
        await update.message.reply_text(
            "Запит скасовано.",
            reply_markup=get_support_keyboard()
        )
        return SUPPORT_MAIN
    
    # Сохраняем запрос в базе данных
    with db_session() as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("Користувач не знайдений. Будь ласка, почніть з /start")
            return ConversationHandler.END
        
        support_request = SupportRequest(
            user_id=user.id,
            message=message_text,
            status="pending"  # pending, answered, closed
        )
        session.add(support_request)
        session.commit()
        request_id = support_request.id
    
    # Отправляем сообщение всем менеджерам
    manager_notification = (
        f"🆘 <b>Новий запит підтримки #{request_id}</b>\n\n"
        f"Від: {update.effective_user.first_name} (@{username}, ID: {user_id})\n"
        f"Повідомлення: {message_text}\n\n"
        f"Для відповіді використовуйте команду /reply {request_id} [ваша відповідь]"
    )
    
    await send_message_to_managers(context.bot, manager_notification)
    
    await update.message.reply_text(
        "✅ Ваш запит успішно відправлено менеджеру!\n"
        "Ми зв'яжемося з вами якнайшвидше.",
        reply_markup=get_support_keyboard()
    )
    
    return SUPPORT_MAIN

async def view_support_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отображает историю запросов в поддержку"""
    user_id = update.effective_user.id
    
    with db_session() as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await update.message.reply_text("Користувач не знайдений. Будь ласка, почніть з /start")
            return ConversationHandler.END
        
        requests = session.query(SupportRequest).filter(
            SupportRequest.user_id == user.id
        ).order_by(SupportRequest.created_at.desc()).limit(5).all()
    
    if not requests:
        await update.message.reply_text(
            "У вас ще немає запитів у підтримку.",
            reply_markup=get_support_keyboard()
        )
        return SUPPORT_MAIN
    
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
    
    await update.message.reply_text(
        history_text,
        reply_markup=get_support_keyboard(),
        parse_mode="HTML"
    )
    
    return SUPPORT_MAIN

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в главное меню"""
    await update.message.reply_text(
        "Повертаємось до головного меню",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    return ConversationHandler.END

def get_support_handlers():
    """Возвращает обработчики для функции поддержки"""
    support_conv = ConversationHandler(
        entry_points=[
            CommandHandler('support', support_command),
            MessageHandler(filters.Regex('^(Підтримка|📞 Підтримка)$'), support_command)
        ],
        states={
            SUPPORT_MAIN: [
                MessageHandler(filters.Regex('^(Новий запит|✉️ Новий запит)$'), start_new_request),
                MessageHandler(filters.Regex('^(Історія запитів|📋 Історія)$'), view_support_history),
                MessageHandler(filters.Regex('^(Назад|🔙 Назад)$'), back_to_main),
            ],
            SENDING_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_support_message),
            ],
        },
        fallbacks=[CommandHandler('cancel', back_to_main)],
    )
    
    return [support_conv]