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
    
    if from_to == "to":
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="currency:back")
        )
    
    return builder.as_markup()


def get_bank_selection():
    """
    Створює інлайн-клавіатуру для вибору банку (для UAH)
    """
    builder = InlineKeyboardBuilder()
    
    banks = [
        {"id": 1, "name": "ПриватБанк"},
        {"id": 2, "name": "Монобанк"},
        {"id": 3, "name": "ПУМБ"}
    ]
    
    for bank in banks:
        builder.row(
            InlineKeyboardButton(
                text=bank["name"],
                callback_data=f"bank:{bank['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="bank:back")
    )
    
    return builder.as_markup()


def get_order_actions(order_id, status):
    """
    Створює інлайн-клавіатуру для дій із заявкою залежно від її статусу
    :param order_id: ID заявки
    :param status: поточний статус заявки
    """
    builder = InlineKeyboardBuilder()
    
    if status == "created":
        builder.row(
            InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"order:confirm:{order_id}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data=f"order:cancel:{order_id}")
        )
    elif status == "awaiting_payment":
        builder.row(
            InlineKeyboardButton(text="💰 Я оплатив", callback_data=f"order:paid:{order_id}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data=f"order:cancel:{order_id}")
        )
    elif status == "payment_confirmed":
        builder.row(
            InlineKeyboardButton(text="✅ Підтвердити оплату", callback_data=f"order:approve:{order_id}"),
            InlineKeyboardButton(text="❌ Відхилити", callback_data=f"order:reject:{order_id}")
        )
    
    return builder.as_markup()


def get_pagination_keyboard(page=1, total_pages=1, prefix="page"):
    """
    Створює інлайн-клавіатуру для пагінації
    :param page: поточна сторінка
    :param total_pages: всього сторінок
    :param prefix: префікс для callback_data
    """
    builder = InlineKeyboardBuilder()
    
    buttons = []
    
    if page > 1:
        buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{page-1}")
        )
    
    buttons.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore")
    )
    
    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{page+1}")
        )
    
    builder.row(*buttons)
    
    return builder.as_markup()


def get_profile_settings():
    """
    Створює інлайн-клавіатуру для налаштувань профілю
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📱 Змінити контакти", callback_data="profile:contacts")
    )
    
    return builder.as_markup()


def get_confirmation_keyboard(action, item_id):
    """
    Створює інлайн-клавіатуру для підтвердження дії
    :param action: дія для підтвердження
    :param item_id: ID елемента
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Так", callback_data=f"confirm:{action}:{item_id}"),
        InlineKeyboardButton(text="❌ Ні", callback_data=f"cancel:{action}:{item_id}")
    )
    
    return builder.as_markup()