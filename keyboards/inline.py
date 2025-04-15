from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_currencies_selection(from_to="from", selected_currency=None):
    builder = InlineKeyboardBuilder()
    
    currencies = [
        {"code": "USDT", "symbol": "₮"},
        {"code": "USD", "symbol": "$"},
        {"code": "UAH", "symbol": "₴"}
    ]
    
    for currency in currencies:
        if selected_currency and currency["code"] == selected_currency:
            continue
        
        builder.row(
            InlineKeyboardButton(
                text=f"{currency['symbol']} {currency['code']}",
                callback_data=f"currency:{from_to}:{currency['code']}"
            )
        )
    
    # Добавляем кнопку "Назад" если это не первый шаг
    if from_to == "to":
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="currency:back")
        )
    
    return builder.as_markup()


def get_bank_selection():
    """
    Создает инлайн-клавиатуру для выбора банка (для UAH)
    """
    builder = InlineKeyboardBuilder()
    
    # Список доступных банков (в реальном приложении будет загружаться из БД)
    banks = [
        {"id": 1, "name": "ПриватБанк"},
        {"id": 2, "name": "Монобанк"},
        {"id": 3, "name": "ПУМБ"}
    ]
    
    # Добавляем кнопки с банками
    for bank in banks:
        builder.row(
            InlineKeyboardButton(
                text=bank["name"],
                callback_data=f"bank:{bank['id']}"
            )
        )
    
    # Добавляем кнопку "Назад"
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="bank:back")
    )
    
    return builder.as_markup()


def get_order_actions(order_id, status):
    """
    Создает инлайн-клавиатуру для действий с заявкой в зависимости от её статуса
    :param order_id: ID заявки
    :param status: текущий статус заявки
    """
    builder = InlineKeyboardBuilder()
    
    if status == "created":
        # Для только что созданной заявки
        builder.row(
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order:confirm:{order_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"order:cancel:{order_id}")
        )
    elif status == "awaiting_payment":
        # Для заявки, ожидающей оплаты
        builder.row(
            InlineKeyboardButton(text="💰 Я оплатил", callback_data=f"order:paid:{order_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"order:cancel:{order_id}")
        )
    elif status == "payment_confirmed":
        # Для заявки с подтвержденной оплатой (для менеджера)
        builder.row(
            InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"order:approve:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order:reject:{order_id}")
        )
    
    return builder.as_markup()


def get_pagination_keyboard(page=1, total_pages=1, prefix="page"):
    """
    Создает инлайн-клавиатуру для пагинации
    :param page: текущая страница
    :param total_pages: всего страниц
    :param prefix: префикс для callback_data
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки для перемещения между страницами
    buttons = []
    
    # Кнопка "Назад"
    if page > 1:
        buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{page-1}")
        )
    
    # Номер текущей страницы
    buttons.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore")
    )
    
    # Кнопка "Вперед"
    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{page+1}")
        )
    
    builder.row(*buttons)
    
    return builder.as_markup()


def get_profile_settings():
    """
    Создает инлайн-клавиатуру для настроек профиля
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔤 Изменить язык", callback_data="profile:language")
    )
    
    builder.row(
        InlineKeyboardButton(text="📱 Изменить контакты", callback_data="profile:contacts")
    )
    
    return builder.as_markup()


def get_confirmation_keyboard(action, item_id):
    """
    Создает инлайн-клавиатуру для подтверждения действия
    :param action: действие для подтверждения
    :param item_id: ID элемента
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{item_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel:{action}:{item_id}")
    )
    
    return builder.as_markup()