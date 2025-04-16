from aiogram import F, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database.models import Order, OrderStatus, User, Currency, Bank
from sqlalchemy import desc
from database.db_operations import get_session
from datetime import datetime

async def show_user_orders(message: types.Message):
    """Показывает историю заявок пользователя"""
    user_id = message.from_user.id
    
    engine = message.bot.get("db_engine")
    session = get_session(engine)
    
    try:
        db_user = session.query(User).filter_by(telegram_id=user_id).first()
        
        if not db_user:
            await message.answer("Помилка при отриманні даних користувача.")
            return
        
        orders = session.query(Order).filter_by(user_id=db_user.id).order_by(desc(Order.created_at)).limit(10).all()
        
        if not orders:
            await message.answer("У вас ще немає жодної заявки на обмін.")
            return
        
        text = "📋 <b>Ваші останні заявки:</b>\n\n"
        
        for order in orders:
            # Получаем данные о валютах
            from_currency = session.query(Currency).filter_by(id=order.from_currency_id).first()
            to_currency = session.query(Currency).filter_by(id=order.to_currency_id).first()
            
            status_emoji = {
                OrderStatus.CREATED: "🆕",
                OrderStatus.AWAITING_PAYMENT: "⏳",
                OrderStatus.PAYMENT_CONFIRMED: "✅",
                OrderStatus.PROCESSING: "⚙️",
                OrderStatus.COMPLETED: "✅",
                OrderStatus.CANCELLED: "❌"
            }
            
            status_text = {
                OrderStatus.CREATED: "Створено",
                OrderStatus.AWAITING_PAYMENT: "Очікує оплати",
                OrderStatus.PAYMENT_CONFIRMED: "Оплату підтверджено",
                OrderStatus.PROCESSING: "В обробці",
                OrderStatus.COMPLETED: "Завершено",
                OrderStatus.CANCELLED: "Скасовано"
            }
            
            text += (
                f"<b>Заявка #{order.id}</b> ({order.created_at.strftime('%d.%m.%Y %H:%M')})\n"
                f"Напрямок: {from_currency.code} → {to_currency.code}\n"
                f"Сума: {order.amount_from:.2f} {from_currency.code} → {order.amount_to:.2f} {to_currency.code}\n"
                f"Статус: {status_emoji.get(order.status, '❓')} {status_text.get(order.status, 'Невідомо')}\n\n"
            )
            
            # Добавляем кнопки действий для активных заявок
            if order.status in [OrderStatus.CREATED, OrderStatus.AWAITING_PAYMENT]:
                builder = InlineKeyboardBuilder()
                builder.row(
                    InlineKeyboardButton(
                        text="📋 Деталі",
                        callback_data=f"order:details:{order.id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Скасувати",
                        callback_data=f"order:cancel:{order.id}"
                    )
                )
                
                await message.answer(text, reply_markup=builder.as_markup())
                text = ""  # Сбрасываем текст для следующей заявки
        
        if text:  # Если остался текст, отправляем его
            await message.answer(text)
    
    except Exception as e:
        await message.answer(f"Помилка при отриманні заявок: {e}")
    finally:
        session.close()

async def show_order_details(callback: types.CallbackQuery):
    """Показывает детали заявки"""
    await callback.answer()
    
    # Получаем ID заявки из callback_data
    order_id = int(callback.data.split(":")[2])
    
    engine = callback.bot.get("db_engine")
    session = get_session(engine)
    
    try:
        # Получаем заявку из БД
        order = session.query(Order).filter_by(id=order_id).first()
        
        if not order:
            await callback.message.answer("Заявку не знайдено.")
            return
        
        # Получаем данные о валютах и банке
        from_currency = session.query(Currency).filter_by(id=order.from_currency_id).first()
        to_currency = session.query(Currency).filter_by(id=order.to_currency_id).first()
        bank = session.query(Bank).filter_by(id=order.bank_id).first() if order.bank_id else None
        
        status_text = {
            OrderStatus.CREATED: "Створено",
            OrderStatus.AWAITING_PAYMENT: "Очікує оплати",
            OrderStatus.PAYMENT_CONFIRMED: "Оплату підтверджено",
            OrderStatus.PROCESSING: "В обробці",
            OrderStatus.COMPLETED: "Завершено",
            OrderStatus.CANCELLED: "Скасовано"
        }
        
        text = (
            f"📋 <b>Деталі заявки #{order.id}</b>\n\n"
            f"Дата створення: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Напрямок: {from_currency.code} → {to_currency.code}\n"
            f"Сума: {order.amount_from:.2f} {from_currency.code} → {order.amount_to:.2f} {to_currency.code}\n"
            f"Курс: 1 {from_currency.code} = {order.rate:.2f} {to_currency.code}\n"
        )
        
        if bank:
            text += f"Банк: {bank.name}\n"
        
        if order.details:
            text += f"Реквізити: <code>{order.details}</code>\n"
        
        text += f"Статус: {status_text.get(order.status, 'Невідомо')}\n"
        
        # Добавляем инструкции в зависимости от статуса
        if order.status == OrderStatus.AWAITING_PAYMENT:
            text += (
                "\n<b>Інструкції для оплати:</b>\n"
                "1. Відправте вказану суму на реквізити:\n"
                "<code>Будуть надані менеджером</code>\n"
                "2. Після оплати натисніть кнопку 'Я оплатив'\n"
                "3. Дочекайтесь підтвердження від менеджера"
            )
        
        # Создаем клавиатуру с действиями
        builder = InlineKeyboardBuilder()
        
        if order.status == OrderStatus.AWAITING_PAYMENT:
            builder.row(
                InlineKeyboardButton(text="💰 Я оплатив", callback_data=f"order:paid:{order.id}")
            )
        
        if order.status in [OrderStatus.CREATED, OrderStatus.AWAITING_PAYMENT]:
            builder.row(
                InlineKeyboardButton(text="❌ Скасувати", callback_data=f"order:cancel:{order.id}")
            )
        
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="order:list")
        )
        
        await callback.message.answer(text, reply_markup=builder.as_markup())
    
    except Exception as e:
        await callback.message.answer(f"Помилка при отриманні деталей заявки: {e}")
    finally:
        session.close()

async def mark_order_as_paid(callback: types.CallbackQuery, session):
    """Отмечает заявку как оплаченную"""
    await callback.answer()
    
    # Получаем ID заявки из callback_data
    order_id = int(callback.data.split(":")[2])
    
    
    try:
        # Получаем заявку из БД
        order = session.query(Order).filter_by(id=order_id).first()
        
        if not order:
            await callback.message.answer("Заявку не знайдено.")
            return
        
        if order.status != OrderStatus.AWAITING_PAYMENT:
            await callback.message.answer("Неможливо позначити заявку як оплачену, оскільки вона не в статусі очікування оплати.")
            return
        
        # Обновляем статус
        order.status = OrderStatus.PAYMENT_CONFIRMED
        order.updated_at = datetime.utcnow()
        session.commit()
        
        await callback.message.answer(
            "✅ Заявку позначено як оплачену!\n\n"
            "Наш менеджер перевірить оплату та підтвердить заявку.\n"
            "Ми повідомимо вас про зміну статусу."
        )
        
        # Отправляем уведомление менеджерам
        # Здесь должен быть код отправки уведомления
    
    except Exception as e:
        await callback.message.answer(f"Помилка при оновленні статусу заявки: {e}")
    finally:
        session.close()

async def cancel_order_by_user(callback: types.CallbackQuery, session):
    """Отмена заявки пользователем"""
    await callback.answer()
    
    # Получаем ID заявки из callback_data
    order_id = int(callback.data.split(":")[2])
    
    try:
        # Получаем заявку из БД
        order = session.query(Order).filter_by(id=order_id).first()
        
        if not order:
            await callback.message.answer("Заявку не знайдено.")
            return
        
        if order.status not in [OrderStatus.CREATED, OrderStatus.AWAITING_PAYMENT]:
            await callback.message.answer("Неможливо скасувати заявку в поточному статусі.")
            return
        
        # Обновляем статус
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        session.commit()
        
        await callback.message.answer("❌ Заявку скасовано.")
        
        # Отправляем уведомление менеджерам
        # Здесь должен быть код отправки уведомления
    
    except Exception as e:
        await callback.message.answer(f"Помилка при скасуванні заявки: {e}")
    finally:
        session.close()

async def show_orders_list(callback: types.CallbackQuery):
    """Возвращает к списку заявок"""
    await callback.answer()
    
    # Создаем новое сообщение со списком заявок
    await show_user_orders(callback.message)

def setup(dp: Dispatcher):
    """Регистрация обработчиков"""
    # Команды меню
    dp.message.register(show_user_orders, F.text(text="📋 Історія"))

    dp.callback_query.register(show_order_details, lambda c: c.data.startswith("order:details:"))
    dp.callback_query.register(mark_order_as_paid, lambda c: c.data.startswith("order:paid:"))
    dp.callback_query.register(cancel_order_by_user, lambda c: c.data.startswith("order:cancel:"))
    dp.callback_query.register(show_orders_list, lambda c: c.data == "order:list")