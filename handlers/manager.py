from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from database import db_session
from database.models import User, Order
from keyboards import get_manager_keyboard, get_main_keyboard
from utils import manager_required

# Состояния для ConversationHandler
MANAGER_MAIN, VIEWING_ORDERS, PROCESSING_ORDER = range(3)

@manager_required
async def manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Открывает панель менеджера"""
    user_id = update.effective_user.id
    
    # Получаем количество активных заявок
    with db_session() as session:
        pending_orders_count = session.query(Order).filter(
            Order.status.in_(["new", "paid"])
        ).count()
    
    await update.message.reply_text(
        f"👨‍💼 <b>Панель менеджера</b>\n\n"
        f"Активні заявки: <b>{pending_orders_count}</b>\n\n"
        f"Виберіть опцію:",
        reply_markup=get_manager_keyboard(),
        parse_mode="HTML"
    )
    
    return MANAGER_MAIN

async def view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отображает список активных заявок"""
    query = update.callback_query
    
    # Если это запрос от Inline-клавиатуры
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    
    context.user_data["page"] = context.user_data.get("page", 0)
    page = context.user_data["page"]
    
    with db_session() as session:
        # Получаем общее количество заявок
        total_orders = session.query(Order).filter(
            Order.status.in_(["new", "paid"])
        ).count()
        
        if total_orders == 0:
            if query:
                await query.edit_message_text(
                    "Немає активних заявок.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data="back_to_manager")
                    ]])
                )
            else:
                await message.reply_text(
                    "Немає активних заявок.",
                    reply_markup=get_manager_keyboard()
                )
            return MANAGER_MAIN
        
        # Получаем заявки для текущей страницы (5 заявок на страницу)
        orders = session.query(Order).filter(
            Order.status.in_(["new", "paid"])
        ).order_by(Order.created_at.desc()).offset(page * 5).limit(5).all()
        
        orders_text = f"📋 <b>Активні заявки</b> (Сторінка {page + 1}/{(total_orders - 1) // 5 + 1})\n\n"
        
        for order in orders:
            # Получаем информацию о пользователе
            user = session.query(User).filter(User.id == order.user_id).first()
            
            status_emoji = "🆕" if order.status == "new" else "💰" if order.status == "paid" else "⏳"
            
            orders_text += f"<b>Заявка #{order.id}</b> {status_emoji} {order.status.upper()}\n"
            orders_text += f"👤 Користувач: {user.first_name} (ID: {user.telegram_id})\n"
            orders_text += f"💱 {order.currency_from} → {order.currency_to}\n"
            orders_text += f"💲 Сума: {order.amount_from} {order.currency_from}\n"
            
            if order.bank_method:
                orders_text += f"🏦 Банк/спосіб: {order.bank_method}\n"
            
            orders_text += f"📅 Створено: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    # Кнопки навигации
    keyboard = [
        [InlineKeyboardButton("Подробиці", callback_data=f"order_{orders[0].id}")] if orders else []
    ]
    
    # Добавляем кнопки навигации по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Попередня", callback_data="prev_page"))
    
    if total_orders > (page + 1) * 5:
        nav_buttons.append(InlineKeyboardButton("➡️ Наступна", callback_data="next_page"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_manager")])
    
    if query:
        await query.edit_message_text(
            orders_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await message.reply_text(
            orders_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    
    return VIEWING_ORDERS

async def handle_order_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает навигацию по списку заявок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "prev_page":
        context.user_data["page"] = max(0, context.user_data.get("page", 0) - 1)
    elif query.data == "next_page":
        context.user_data["page"] = context.user_data.get("page", 0) + 1
    elif query.data == "back_to_manager":
        return await manager_command(update, context)
    
    return await view_orders(update, context)

async def view_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отображает детали заявки и предлагает действия"""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID заявки из callback_data
    order_id = int(query.data.split('_')[1])
    
    with db_session() as session:
        order = session.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            await query.edit_message_text(
                "Заявка не знайдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_orders")
                ]])
            )
            return VIEWING_ORDERS
        
        # Получаем информацию о пользователе
        user = session.query(User).filter(User.id == order.user_id).first()
        
        # Формируем подробную информацию о заявке
        details_text = f"📝 <b>Деталі заявки #{order.id}</b>\n\n"
        details_text += f"<b>Статус:</b> {order.status.upper()}\n"
        details_text += f"<b>Створено:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        details_text += f"<b>Користувач:</b> {user.first_name}\n"
        details_text += f"<b>Telegram ID:</b> {user.telegram_id}\n"
        
        if user.contact_info:
            details_text += f"<b>Контактна інформація:</b> {user.contact_info}\n\n"
        else:
            details_text += "<b>Контактна інформація:</b> Не вказана\n\n"
        
        details_text += f"<b>Напрямок обміну:</b> {order.currency_from} → {order.currency_to}\n"
        details_text += f"<b>Сума відправлення:</b> {order.amount_from} {order.currency_from}\n"
        details_text += f"<b>Сума отримання:</b> {order.amount_to} {order.currency_to}\n"
        details_text += f"<b>Курс:</b> {order.rate}\n"
        
        if order.bank_method:
            details_text += f"<b>Банк/спосіб:</b> {order.bank_method}\n"
        
        if order.payment_details:
            details_text += f"\n<b>Деталі оплати:</b>\n{order.payment_details}\n"
        
        # Кнопки действий в зависимости от статуса заявки
        keyboard = []
        
        if order.status == "new":
            keyboard.append([
                InlineKeyboardButton("✅ Підтвердити заявку", callback_data=f"confirm_{order.id}"),
                InlineKeyboardButton("❌ Відхилити", callback_data=f"reject_{order.id}")
            ])
        elif order.status == "paid":
            keyboard.append([
                InlineKeyboardButton("✅ Завершити заявку", callback_data=f"complete_{order.id}"),
                InlineKeyboardButton("❌ Відхилити", callback_data=f"reject_{order.id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад до списку", callback_data="back_to_orders")])
    
    await query.edit_message_text(
        details_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return PROCESSING_ORDER

async def process_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает действия менеджера с заявкой"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_orders":
        context.user_data["page"] = 0  # Сбрасываем страницу
        return await view_orders(update, context)
    
    # Получаем действие и ID заявки
    action, order_id = query.data.split('_')
    order_id = int(order_id)
    
    with db_session() as session:
        order = session.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            await query.edit_message_text(
                "Заявка не знайдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_orders")
                ]])
            )
            return VIEWING_ORDERS
        
        # Получаем информацию о пользователе для уведомления
        user = session.query(User).filter(User.id == order.user_id).first()
        
        # Обрабатываем действие
        if action == "confirm":
            order.status = "confirmed"
            status_message = "✅ Заявку підтверджено"
            user_message = (
                f"✅ Вашу заявку #{order.id} підтверджено менеджером!\n\n"
                f"Будь ласка, виконайте оплату згідно з інструкціями та натисніть "
                f"кнопку \"Я оплатив\" у вашому меню заявок."
            )
        elif action == "complete":
            order.status = "completed"
            status_message = "✅ Заявку завершено"
            user_message = (
                f"🎉 Вашу заявку #{order.id} успішно завершено!\n\n"
                f"Дякуємо за використання нашого сервісу."
            )
        elif action == "reject":
            order.status = "rejected"
            status_message = "❌ Заявку відхилено"
            user_message = (
                f"❌ На жаль, вашу заявку #{order.id} було відхилено.\n\n"
                f"Для отримання додаткової інформації, будь ласка, зв'яжіться з менеджером."
            )
        
        session.commit()
    
    # Отправляем уведомление пользователю
    try:
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text=user_message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не вдалося надіслати повідомлення користувачу {user.telegram_id}: {e}")
    
    # Сообщаем менеджеру о результате
    await query.edit_message_text(
        f"{status_message} (ID: {order_id}).\n"
        f"Користувач отримав повідомлення про зміну статусу.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад до списку", callback_data="back_to_orders")
        ]])
    )
    
    return PROCESSING_ORDER

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в главное меню"""
    await update.message.reply_text(
        "Повертаємось до головного меню",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    return ConversationHandler.END

def get_manager_handlers():
    """Возвращает обработчики для функционала менеджера"""
    manager_conv = ConversationHandler(
        entry_points=[
            CommandHandler('manager', manager_command),
            MessageHandler(filters.Regex('^(Панель менеджера|👨‍💼 Панель менеджера)$'), manager_command)
        ],
        states={
            MANAGER_MAIN: [
                MessageHandler(filters.Regex('^(Активні заявки|📋 Заявки)$'), view_orders),
                MessageHandler(filters.Regex('^(Головне меню|🔙 Назад)$'), back_to_main),
            ],
            VIEWING_ORDERS: [
                CallbackQueryHandler(view_order_details, pattern=r'^order_\d+$'),
                CallbackQueryHandler(handle_order_navigation),
            ],
            PROCESSING_ORDER: [
                CallbackQueryHandler(process_order_action),
            ],
        },
        fallbacks=[CommandHandler('cancel', back_to_main)],
    )
    
    return [manager_conv]