from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackContext, ConversationHandler, 
    MessageHandler, CallbackQueryHandler, filters
)
from datetime import datetime

from database.models import User, ExchangeRate, Bank, PaymentMethod, Currency, Commission
from utils import admin_required
from keyboards import get_admin_keyboard

# Состояния для ConversationHandler
(
    ADMIN_MENU, RATES_MENU, CURRENCY_MENU, BANK_MENU, 
    PAYMENT_METHOD_MENU, COMMISSION_MENU, MANAGER_MENU,
    
    # Состояния для обновления курсов
    SELECT_CURRENCY_PAIR, INPUT_NEW_RATE,
    
    # Состояния для управления валютами
    ADD_CURRENCY_NAME, ADD_CURRENCY_CODE, ADD_CURRENCY_TYPE,
    REMOVE_CURRENCY_CONFIRM,
    
    # Состояния для управления банками
    ADD_BANK_NAME, ADD_BANK_DETAILS,
    REMOVE_BANK_CONFIRM,
    
    # Состояния для управления способами оплаты
    ADD_PAYMENT_METHOD_NAME, ADD_PAYMENT_METHOD_DETAILS,
    REMOVE_PAYMENT_METHOD_CONFIRM,
    
    # Состояния для управления комиссиями
    SELECT_COMMISSION_PAIR, INPUT_COMMISSION_VALUE,
    
    # Состояния для управления менеджерами
    ADD_MANAGER_USER_ID, REMOVE_MANAGER_CONFIRM
) = range(25)

# Обработчик команды /admin
@admin_required
def admin_command(update: Update, context: CallbackContext) -> int:
    """Обработка команды /admin для доступа к административной панели"""
    user = update.effective_user
    
    reply_markup = get_admin_keyboard()
    update.message.reply_text(
        f"👨‍💼 Административная панель Changify\n\n"
        f"Выберите раздел для управления:",
        reply_markup=reply_markup
    )
    
    return ADMIN_MENU

# === Управление курсами валют ===

@admin_required
def rates_menu(update: Update, context: CallbackContext) -> int:
    """Показать меню управления курсами валют"""
    query = update.callback_query
    query.answer()
    
    # Получить все текущие курсы валют
    rates = ExchangeRate.get_all_rates()
    
    keyboard = []
    for rate in rates:
        pair_name = f"{rate.from_currency.code}/{rate.to_currency.code}"
        rate_value = f"{rate.rate:.4f}"
        keyboard.append([InlineKeyboardButton(
            f"{pair_name}: {rate_value}",
            callback_data=f"edit_rate_{rate.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить новую пару", callback_data="add_rate")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "💱 Управление курсами валют\n\n"
        "Текущие курсы: \n"
        "Выберите пару для редактирования или добавьте новую:",
        reply_markup=reply_markup
    )
    
    return RATES_MENU

@admin_required
def add_rate_select_pair(update: Update, context: CallbackContext) -> int:
    """Первый шаг добавления курса - выбор валютной пары"""
    query = update.callback_query
    query.answer()
    
    # Получить все доступные валюты
    currencies = Currency.get_all_currencies()
    
    # Создаем список всех возможных пар
    pairs = []
    for base_currency in currencies:
        for quote_currency in currencies:
            if base_currency.id != quote_currency.id:
                pairs.append(f"{base_currency.code}/{quote_currency.code}")
    
    # Создаем клавиатуру с парами
    keyboard = []
    for pair in pairs:
        keyboard.append([InlineKeyboardButton(pair, callback_data=f"pair_{pair}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_rates")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "Выберите валютную пару для добавления/обновления курса:",
        reply_markup=reply_markup
    )
    
    return SELECT_CURRENCY_PAIR

@admin_required
def input_new_rate(update: Update, context: CallbackContext) -> int:
    """Второй шаг добавления/обновления курса - ввод нового курса"""
    query = update.callback_query
    query.answer()
    
    # Получаем выбранную пару из callback_data
    pair = query.data.replace("pair_", "")
    context.user_data["selected_pair"] = pair
    
    base_code, quote_code = pair.split("/")
    
    query.edit_message_text(
        f"Введите новый курс обмена для пары {pair}:\n"
        f"(например, для {base_code}/{quote_code} = 1.05, введите 1.05)"
    )
    
    return INPUT_NEW_RATE

@admin_required
def save_new_rate(update: Update, context: CallbackContext) -> int:
    """Сохранение нового курса валют"""
    try:
        new_rate = float(update.message.text.strip())
        if new_rate <= 0:
            update.message.reply_text(
                "❌ Ошибка: Курс должен быть положительным числом. Попробуйте снова:"
            )
            return INPUT_NEW_RATE
        
        pair = context.user_data.get("selected_pair")
        base_code, quote_code = pair.split("/")
        
        # Получаем валюты из базы данных
        base_currency = Currency.get_by_code(base_code)
        quote_currency = Currency.get_by_code(quote_code)
        
        if not base_currency or not quote_currency:
            update.message.reply_text("❌ Ошибка: Одна из валют не найдена в базе данных.")
            return rates_menu(update, context)
        
        # Проверяем, существует ли уже такой курс
        existing_rate = ExchangeRate.get_rate(base_currency.id, quote_currency.id)
        
        if existing_rate:
            # Обновляем существующий курс
            ExchangeRate.update_rate(
                base_currency.id, 
                quote_currency.id, 
                new_rate
            )
            message = f"✅ Курс для пары {pair} успешно обновлен на {new_rate}"
        else:
            # Создаем новый курс
            ExchangeRate.create(
                from_currency_id=base_currency.id,
                to_currency_id=quote_currency.id,
                rate=new_rate
            )
            message = f"✅ Новый курс для пары {pair} успешно добавлен: {new_rate}"
        
        update.message.reply_text(message)
        
        # Очищаем данные пользователя
        if "selected_pair" in context.user_data:
            del context.user_data["selected_pair"]
        
        # Возвращаемся к клавиатуре администратора
        reply_markup = get_admin_keyboard()
        update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        return ADMIN_MENU
        
    except ValueError:
        update.message.reply_text(
            "❌ Ошибка: Введите корректное число. Например: 1.05"
        )
        return INPUT_NEW_RATE

# === Управление валютами ===

@admin_required
def currency_menu(update: Update, context: CallbackContext) -> int:
    """Показать меню управления валютами"""
    query = update.callback_query
    query.answer()
    
    # Получить все валюты
    currencies = Currency.get_all_currencies()
    
    keyboard = []
    for currency in currencies:
        keyboard.append([InlineKeyboardButton(
            f"{currency.code} - {currency.name} ({currency.type})",
            callback_data=f"currency_{currency.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить валюту", callback_data="add_currency")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "💰 Управление валютами\n\n"
        "Текущие валюты: \n"
        "Выберите валюту для управления или добавьте новую:",
        reply_markup=reply_markup
    )
    
    return CURRENCY_MENU

@admin_required
def add_currency_name(update: Update, context: CallbackContext) -> int:
    """Запрос названия новой валюты"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "Введите название новой валюты (например, 'Доллар США'):"
    )
    
    return ADD_CURRENCY_NAME

@admin_required
def add_currency_code(update: Update, context: CallbackContext) -> int:
    """Запрос кода новой валюты"""
    # Сохраняем название валюты
    context.user_data["new_currency_name"] = update.message.text.strip()
    
    update.message.reply_text(
        "Введите код валюты (например, 'USD'):"
    )
    
    return ADD_CURRENCY_CODE

@admin_required
def add_currency_type(update: Update, context: CallbackContext) -> int:
    """Запрос типа новой валюты"""
    # Сохраняем код валюты
    context.user_data["new_currency_code"] = update.message.text.strip().upper()
    
    keyboard = [
        [InlineKeyboardButton("Фиат", callback_data="type_fiat")],
        [InlineKeyboardButton("Криптовалюта", callback_data="type_crypto")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "Выберите тип валюты:",
        reply_markup=reply_markup
    )
    
    return ADD_CURRENCY_TYPE

@admin_required
def save_new_currency(update: Update, context: CallbackContext) -> int:
    """Сохранение новой валюты"""
    query = update.callback_query
    query.answer()
    
    currency_type = "fiat" if query.data == "type_fiat" else "crypto"
    
    # Получаем данные из контекста
    name = context.user_data.get("new_currency_name")
    code = context.user_data.get("new_currency_code")
    
    try:
        # Проверяем, существует ли уже валюта с таким кодом
        existing_currency = Currency.get_by_code(code)
        
        if existing_currency:
            query.edit_message_text(
                f"❌ Ошибка: Валюта с кодом {code} уже существует."
            )
        else:
            # Создаем новую валюту
            Currency.create(
                name=name,
                code=code,
                type=currency_type
            )
            
            query.edit_message_text(
                f"✅ Новая валюта успешно добавлена:\n"
                f"Название: {name}\n"
                f"Код: {code}\n"
                f"Тип: {currency_type}"
            )
        
        # Очищаем данные пользователя
        if "new_currency_name" in context.user_data:
            del context.user_data["new_currency_name"]
        if "new_currency_code" in context.user_data:
            del context.user_data["new_currency_code"]
        
        # Возвращаемся к клавиатуре администратора
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Выберите действие:",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
        
    except Exception as e:
        query.edit_message_text(
            f"❌ Ошибка при добавлении валюты: {str(e)}"
        )
        return currency_menu(update, context)

@admin_required
def remove_currency(update: Update, context: CallbackContext) -> int:
    """Запрос подтверждения удаления валюты"""
    query = update.callback_query
    query.answer()
    
    currency_id = int(query.data.split("_")[1])
    context.user_data["currency_to_remove"] = currency_id
    
    currency = Currency.get_by_id(currency_id)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_remove_currency"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel_remove_currency")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"Вы уверены, что хотите удалить валюту {currency.code} - {currency.name}?\n\n"
        f"⚠️ Внимание: Это действие также удалит все связанные курсы обмена!",
        reply_markup=reply_markup
    )
    
    return REMOVE_CURRENCY_CONFIRM

@admin_required
def remove_currency_confirm(update: Update, context: CallbackContext) -> int:
    """Подтверждение удаления валюты"""
    query = update.callback_query
    query.answer()
    
    if query.data == "confirm_remove_currency":
        currency_id = context.user_data.get("currency_to_remove")
        
        if currency_id:
            currency = Currency.get_by_id(currency_id)
            
            if currency:
                # Удаляем связанные курсы
                ExchangeRate.delete_rates_by_currency(currency_id)
                
                # Удаляем валюту
                Currency.delete(currency_id)
                
                query.edit_message_text(
                    f"✅ Валюта {currency.code} успешно удалена вместе со связанными курсами."
                )
            else:
                query.edit_message_text(
                    "❌ Ошибка: Валюта не найдена."
                )
    else:
        query.edit_message_text(
            "❌ Удаление валюты отменено."
        )
    
    # Очищаем данные пользователя
    if "currency_to_remove" in context.user_data:
        del context.user_data["currency_to_remove"]
    
    # Возвращаемся к клавиатуре администратора
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    return ADMIN_MENU

# === Управление банками ===

@admin_required
def bank_menu(update: Update, context: CallbackContext) -> int:
    """Показать меню управления банками"""
    query = update.callback_query
    query.answer()
    
    # Получить все банки
    banks = Bank.get_all()
    
    keyboard = []
    for bank in banks:
        keyboard.append([InlineKeyboardButton(
            f"{bank.name}",
            callback_data=f"bank_{bank.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить банк", callback_data="add_bank")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🏦 Управление банками\n\n"
        "Текущие банки: \n"
        "Выберите банк для управления или добавьте новый:",
        reply_markup=reply_markup
    )
    
    return BANK_MENU

@admin_required
def add_bank_name(update: Update, context: CallbackContext) -> int:
    """Запрос названия нового банка"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "Введите название нового банка (например, 'ПриватБанк'):"
    )
    
    return ADD_BANK_NAME

@admin_required
def add_bank_details(update: Update, context: CallbackContext) -> int:
    """Запрос деталей нового банка"""
    # Сохраняем название банка
    context.user_data["new_bank_name"] = update.message.text.strip()
    
    update.message.reply_text(
        "Введите детали банка (например, инструкции по оплате):"
    )
    
    return ADD_BANK_DETAILS

@admin_required
def save_new_bank(update: Update, context: CallbackContext) -> int:
    """Сохранение нового банка"""
    # Сохраняем детали банка
    bank_details = update.message.text.strip()
    bank_name = context.user_data.get("new_bank_name")
    
    try:
        # Создаем новый банк
        Bank.create(
            name=bank_name,
            details=bank_details
        )
        
        update.message.reply_text(
            f"✅ Новый банк успешно добавлен:\n"
            f"Название: {bank_name}\n"
            f"Детали: {bank_details}"
        )
        
        # Очищаем данные пользователя
        if "new_bank_name" in context.user_data:
            del context.user_data["new_bank_name"]
        
        # Возвращаемся к клавиатуре администратора
        reply_markup = get_admin_keyboard()
        update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        return ADMIN_MENU
        
    except Exception as e:
        update.message.reply_text(
            f"❌ Ошибка при добавлении банка: {str(e)}"
        )
        return bank_menu(update, context)

@admin_required
def remove_bank(update: Update, context: CallbackContext) -> int:
    """Запрос подтверждения удаления банка"""
    query = update.callback_query
    query.answer()
    
    bank_id = int(query.data.split("_")[1])
    context.user_data["bank_to_remove"] = bank_id
    
    bank = Bank.get_by_id(bank_id)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_remove_bank"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel_remove_bank")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"Вы уверены, что хотите удалить банк {bank.name}?",
        reply_markup=reply_markup
    )
    
    return REMOVE_BANK_CONFIRM

@admin_required
def remove_bank_confirm(update: Update, context: CallbackContext) -> int:
    """Подтверждение удаления банка"""
    query = update.callback_query
    query.answer()
    
    if query.data == "confirm_remove_bank":
        bank_id = context.user_data.get("bank_to_remove")
        
        if bank_id:
            bank = Bank.get_by_id(bank_id)
            
            if bank:
                # Удаляем банк
                Bank.delete(bank_id)
                
                query.edit_message_text(
                    f"✅ Банк {bank.name} успешно удален."
                )
            else:
                query.edit_message_text(
                    "❌ Ошибка: Банк не найден."
                )
    else:
        query.edit_message_text(
            "❌ Удаление банка отменено."
        )
    
    # Очищаем данные пользователя
    if "bank_to_remove" in context.user_data:
        del context.user_data["bank_to_remove"]
    
    # Возвращаемся к клавиатуре администратора
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    return ADMIN_MENU

# === Управление методами оплаты ===

@admin_required
def payment_method_menu(update: Update, context: CallbackContext) -> int:
    """Показать меню управления методами оплаты"""
    query = update.callback_query
    query.answer()
    
    # Получить все методы оплаты
    payment_methods = PaymentMethod.get_all()
    
    keyboard = []
    for method in payment_methods:
        keyboard.append([InlineKeyboardButton(
            f"{method.name}",
            callback_data=f"payment_method_{method.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить метод оплаты", callback_data="add_payment_method")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "💳 Управление методами оплаты\n\n"
        "Текущие методы оплаты: \n"
        "Выберите метод для управления или добавьте новый:",
        reply_markup=reply_markup
    )
    
    return PAYMENT_METHOD_MENU

@admin_required
def add_payment_method_name(update: Update, context: CallbackContext) -> int:
    """Запрос названия нового метода оплаты"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "Введите название нового метода оплаты (например, 'PayPal'):"
    )
    
    return ADD_PAYMENT_METHOD_NAME

@admin_required
def add_payment_method_details(update: Update, context: CallbackContext) -> int:
    """Запрос деталей нового метода оплаты"""
    # Сохраняем название метода оплаты
    context.user_data["new_payment_method_name"] = update.message.text.strip()
    
    update.message.reply_text(
        "Введите детали метода оплаты (например, инструкции):"
    )
    
    return ADD_PAYMENT_METHOD_DETAILS

@admin_required
def save_new_payment_method(update: Update, context: CallbackContext) -> int:
    """Сохранение нового метода оплаты"""
    # Сохраняем детали метода оплаты
    payment_method_details = update.message.text.strip()
    payment_method_name = context.user_data.get("new_payment_method_name")
    
    try:
        # Создаем новый метод оплаты
        PaymentMethod.create(
            name=payment_method_name,
            details=payment_method_details
        )
        
        update.message.reply_text(
            f"✅ Новый метод оплаты успешно добавлен:\n"
            f"Название: {payment_method_name}\n"
            f"Детали: {payment_method_details}"
        )
        
        # Очищаем данные пользователя
        if "new_payment_method_name" in context.user_data:
            del context.user_data["new_payment_method_name"]
        
        # Возвращаемся к клавиатуре администратора
        reply_markup = get_admin_keyboard()
        update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        return ADMIN_MENU
        
    except Exception as e:
        update.message.reply_text(
            f"❌ Ошибка при добавлении метода оплаты: {str(e)}"
        )
        return payment_method_menu(update, context)

@admin_required
def remove_payment_method(update: Update, context: CallbackContext) -> int:
    """Запрос подтверждения удаления метода оплаты"""
    query = update.callback_query
    query.answer()
    
    payment_method_id = int(query.data.split("_")[2])
    context.user_data["payment_method_to_remove"] = payment_method_id
    
    payment_method = PaymentMethod.get_by_id(payment_method_id)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_remove_payment_method"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel_remove_payment_method")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"Вы уверены, что хотите удалить метод оплаты {payment_method.name}?",
        reply_markup=reply_markup
    )
    
    return REMOVE_PAYMENT_METHOD_CONFIRM

@admin_required
def remove_payment_method_confirm(update: Update, context: CallbackContext) -> int:
    """Подтверждение удаления метода оплаты"""
    query = update.callback_query
    query.answer()
    
    if query.data == "confirm_remove_payment_method":
        payment_method_id = context.user_data.get("payment_method_to_remove")
        
        if payment_method_id:
            payment_method = PaymentMethod.get_by_id(payment_method_id)
            
            if payment_method:
                # Удаляем метод оплаты
                PaymentMethod.delete(payment_method_id)
                
                query.edit_message_text(
                    f"✅ Метод оплаты {payment_method.name} успешно удален."
                )
            else:
                query.edit_message_text(
                    "❌ Ошибка: Метод оплаты не найден."
                )
    else:
        query.edit_message_text(
            "❌ Удаление метода оплаты отменено."
        )
    
    # Очищаем данные пользователя
    if "payment_method_to_remove" in context.user_data:
        del context.user_data["payment_method_to_remove"]
    
    # Возвращаемся к клавиатуре администратора
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    return ADMIN_MENU

# === Управление комиссиями ===

@admin_required
def commission_menu(update: Update, context: CallbackContext) -> int:
    """Показать меню управления комиссиями"""
    query = update.callback_query
    query.answer()
    
    # Получить все комиссии
    commissions = Commission.get_all()
    
    keyboard = []
    for commission in commissions:
        pair_name = f"{commission.from_currency.code}/{commission.to_currency.code}"
        keyboard.append([InlineKeyboardButton(
            f"{pair_name}: {commission.value}%",
            callback_data=f"commission_{commission.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить комиссию", callback_data="add_commission")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "💸 Управление комиссиями\n\n"
        "Текущие комиссии: \n"
        "Выберите комиссию для управления или добавьте новую:",
        reply_markup=reply_markup
    )
    
    return COMMISSION_MENU

@admin_required
def add_commission_select_pair(update: Update, context: CallbackContext) -> int:
    """Первый шаг добавления комиссии - выбор валютной пары"""
    query = update.callback_query
    query.answer()
    
    # Получить все доступные валюты
    currencies = Currency.get_all_currencies()
    
    # Создаем список всех возможных пар
    pairs = []
    for base_currency in currencies:
        for quote_currency in currencies:
            if base_currency.id != quote_currency.id:
                pairs.append(f"{base_currency.code}/{quote_currency.code}")
    
    # Создаем клавиатуру с парами
    keyboard = []
    for pair in pairs:
        keyboard.append([InlineKeyboardButton(pair, callback_data=f"commission_pair_{pair}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_commissions")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "Выберите валютную пару для добавления/обновления комиссии:",
        reply_markup=reply_markup
    )
    
    return SELECT_COMMISSION_PAIR

@admin_required
def input_commission_value(update: Update, context: CallbackContext) -> int:
    """Второй шаг добавления/обновления комиссии - ввод значения комиссии"""
    query = update.callback_query
    query.answer()
    
    # Получаем выбранную пару из callback_data
    pair = query.data.replace("commission_pair_", "")
    context.user_data["selected_commission_pair"] = pair
    
    base_code, quote_code = pair.split("/")
    
    query.edit_message_text(
        f"Введите значение комиссии в процентах для пары {pair}:\n"
        f"(например, для комиссии 2%, введите 2.0)"
    )
    
    return INPUT_COMMISSION_VALUE

@admin_required
def save_new_commission(update: Update, context: CallbackContext) -> int:
    """Сохранение новой комиссии"""
    try:
        commission_value = float(update.message.text.strip())
        if commission_value < 0:
            update.message.reply_text(
                "❌ Ошибка: Комиссия не может быть отрицательной. Попробуйте снова:"
            )
            return INPUT_COMMISSION_VALUE
        
        pair = context.user_data.get("selected_commission_pair")
        base_code, quote_code = pair.split("/")
        
        # Получаем валюты из базы данных
        base_currency = Currency.get_by_code(base_code)
        quote_currency = Currency.get_by_code(quote_code)
        
        if not base_currency or not quote_currency:
            update.message.reply_text("❌ Ошибка: Одна из валют не найдена в базе данных.")
            return commission_menu(update, context)
        
        # Проверяем, существует ли уже такая комиссия
        existing_commission = Commission.get_by_currencies(base_currency.id, quote_currency.id)
        
        if existing_commission:
            # Обновляем существующую комиссию
            Commission.update(
                existing_commission.id,
                commission_value
            )
            message = f"✅ Комиссия для пары {pair} успешно обновлена на {commission_value}%"
        else:
            # Создаем новую комиссию
            Commission.create(
                from_currency_id=base_currency.id,
                to_currency_id=quote_currency.id,
                value=commission_value
            )
            message = f"✅ Новая комиссия для пары {pair} успешно добавлена: {commission_value}%"
        
        update.message.reply_text(message)
        
        # Очищаем данные пользователя
        if "selected_commission_pair" in context.user_data:
            del context.user_data["selected_commission_pair"]
        
        # Возвращаемся к клавиатуре администратора
        reply_markup = get_admin_keyboard()
        update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        return ADMIN_MENU
        
    except ValueError:
        update.message.reply_text(
            "❌ Ошибка: Введите корректное число. Например: 2.0"
        )
        return INPUT_COMMISSION_VALUE

@admin_required
def remove_commission(update: Update, context: CallbackContext) -> int:
    """Удаление комиссии"""
    query = update.callback_query
    query.answer()
    
    commission_id = int(query.data.split("_")[1])
    commission = Commission.get_by_id(commission_id)
    
    if commission:
        # Удаляем комиссию
        Commission.delete(commission_id)
        pair_name = f"{commission.from_currency.code}/{commission.to_currency.code}"
        
        query.edit_message_text(
            f"✅ Комиссия для пары {pair_name} успешно удалена."
        )
    else:
        query.edit_message_text(
            "❌ Ошибка: Комиссия не найдена."
        )
    
    # Возвращаемся к меню комиссий
    return commission_menu(update, context)

# === Управление менеджерами ===

@admin_required
def manager_menu(update: Update, context: CallbackContext) -> int:
    """Показать меню управления менеджерами"""
    query = update.callback_query
    query.answer()
    
    # Получить всех менеджеров
    managers = User.get_managers()
    
    keyboard = []
    for manager in managers:
        display_name = f"{manager.first_name}"
        if manager.last_name:
            display_name += f" {manager.last_name}"
        if manager.username:
            display_name += f" (@{manager.username})"
            
        keyboard.append([InlineKeyboardButton(
            display_name,
            callback_data=f"manager_{manager.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить менеджера", callback_data="add_manager")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "👨‍💼 Управление менеджерами\n\n"
        "Текущие менеджеры: \n"
        "Выберите менеджера для управления или добавьте нового:",
        reply_markup=reply_markup
    )
    
    return MANAGER_MENU

@admin_required
def add_manager_user_id(update: Update, context: CallbackContext) -> int:
    """Запрос ID пользователя для добавления в менеджеры"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "Введите Telegram ID пользователя, которого нужно назначить менеджером:\n"
        "(Пользователь должен быть зарегистрирован в боте)"
    )
    
    return ADD_MANAGER_USER_ID

@admin_required
def save_new_manager(update: Update, context: CallbackContext) -> int:
    """Сохранение нового менеджера"""
    try:
        user_id = int(update.message.text.strip())
        
        # Проверяем, существует ли такой пользователь
        user = User.get_by_telegram_id(user_id)
        
        if not user:
            update.message.reply_text(
                "❌ Ошибка: Пользователь с таким ID не найден. Пользователь должен быть зарегистрирован в боте."
            )
            return ADD_MANAGER_USER_ID
        
        # Проверяем, не является ли уже пользователь менеджером
        if user.role == 'manager':
            update.message.reply_text(
                f"❌ Пользователь {user.first_name} уже является менеджером."
            )
        elif user.role == 'admin':
            update.message.reply_text(
                f"❌ Пользователь {user.first_name} является администратором, нет необходимости назначать его менеджером."
            )
        else:
            # Назначаем пользователя менеджером
            User.update_role(user.id, 'manager')
            
            update.message.reply_text(
                f"✅ Пользователь {user.first_name} {user.last_name if user.last_name else ''} "
                f"успешно назначен менеджером."
            )
        
        # Возвращаемся к клавиатуре администратора
        reply_markup = get_admin_keyboard()
        update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        return ADMIN_MENU
        
    except ValueError:
        update.message.reply_text(
            "❌ Ошибка: Введите корректный числовой ID пользователя."
        )
        return ADD_MANAGER_USER_ID

@admin_required
def remove_manager(update: Update, context: CallbackContext) -> int:
    """Запрос подтверждения удаления менеджера"""
    query = update.callback_query
    query.answer()
    
    manager_id = int(query.data.split("_")[1])
    context.user_data["manager_to_remove"] = manager_id
    
    manager = User.get_by_id(manager_id)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_remove_manager"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel_remove_manager")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    display_name = f"{manager.first_name}"
    if manager.last_name:
        display_name += f" {manager.last_name}"
    if manager.username:
        display_name += f" (@{manager.username})"
    
    query.edit_message_text(
        f"Вы уверены, что хотите удалить менеджера {display_name}?",
        reply_markup=reply_markup
    )
    
    return REMOVE_MANAGER_CONFIRM

@admin_required
def remove_manager_confirm(update: Update, context: CallbackContext) -> int:
    """Подтверждение удаления менеджера"""
    query = update.callback_query
    query.answer()
    
    if query.data == "confirm_remove_manager":
        manager_id = context.user_data.get("manager_to_remove")
        
        if manager_id:
            manager = User.get_by_id(manager_id)
            
            if manager:
                # Понижаем роль менеджера до пользователя
                User.update_role(manager.id, 'user')
                
                display_name = f"{manager.first_name}"
                if manager.last_name:
                    display_name += f" {manager.last_name}"
                
                query.edit_message_text(
                    f"✅ {display_name} больше не является менеджером."
                )
            else:
                query.edit_message_text(
                    "❌ Ошибка: Менеджер не найден."
                )
    else:
        query.edit_message_text(
            "❌ Удаление менеджера отменено."
        )
    
    # Очищаем данные пользователя
    if "manager_to_remove" in context.user_data:
        del context.user_data["manager_to_remove"]
    
    # Возвращаемся к клавиатуре администратора
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    return ADMIN_MENU

# === Обработчики для возврата в предыдущие меню ===

@admin_required
def back_to_admin(update: Update, context: CallbackContext) -> int:
    """Возврат в главное меню администратора"""
    query = update.callback_query
    query.answer()
    
    reply_markup = get_admin_keyboard()
    query.edit_message_text(
        "👨‍💼 Административная панель Changify\n\n"
        "Выберите раздел для управления:",
        reply_markup=reply_markup
    )
    
    return ADMIN_MENU

@admin_required
def back_to_rates(update: Update, context: CallbackContext) -> int:
    """Возврат в меню управления курсами"""
    return rates_menu(update, context)

@admin_required
def back_to_currencies(update: Update, context: CallbackContext) -> int:
    """Возврат в меню управления валютами"""
    return currency_menu(update, context)

@admin_required
def back_to_banks(update: Update, context: CallbackContext) -> int:
    """Возврат в меню управления банками"""
    return bank_menu(update, context)

@admin_required
def back_to_payment_methods(update: Update, context: CallbackContext) -> int:
    """Возврат в меню управления методами оплаты"""
    return payment_method_menu(update, context)

@admin_required
def back_to_commissions(update: Update, context: CallbackContext) -> int:
    """Возврат в меню управления комиссиями"""
    return commission_menu(update, context)

@admin_required
def back_to_managers(update: Update, context: CallbackContext) -> int:
    """Возврат в меню управления менеджерами"""
    return manager_menu(update, context)

# === Регистрация обработчиков ===

def register_admin_handlers(dispatcher):
    """Регистрация всех обработчиков администратора"""
    
    # ConversationHandler для административной панели
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_command)],
        states={
            ADMIN_MENU: [
                CallbackQueryHandler(rates_menu, pattern='^rates$'),
                CallbackQueryHandler(currency_menu, pattern='^currencies$'),
                CallbackQueryHandler(bank_menu, pattern='^banks$'),
                CallbackQueryHandler(payment_method_menu, pattern='^payment_methods$'),
                CallbackQueryHandler(commission_menu, pattern='^commissions$'),
                CallbackQueryHandler(manager_menu, pattern='^managers$'),
            ],
            
            # Состояния для управления курсами
            RATES_MENU: [
                CallbackQueryHandler(add_rate_select_pair, pattern='^add_rate$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                CallbackQueryHandler(rates_menu, pattern='^edit_rate_\d+$'),
            ],
            SELECT_CURRENCY_PAIR: [
                CallbackQueryHandler(input_new_rate, pattern='^pair_\w+/\w+$'),
                CallbackQueryHandler(back_to_rates, pattern='^back_to_rates$'),
            ],
            INPUT_NEW_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_rate),
            ],
            
            # Состояния для управления валютами
            CURRENCY_MENU: [
                CallbackQueryHandler(add_currency_name, pattern='^add_currency$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                CallbackQueryHandler(remove_currency, pattern='^currency_\d+$'),
            ],
            ADD_CURRENCY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_currency_code),
            ],
            ADD_CURRENCY_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_currency_type),
            ],
            ADD_CURRENCY_TYPE: [
                CallbackQueryHandler(save_new_currency, pattern='^type_(fiat|crypto)$'),
            ],
            REMOVE_CURRENCY_CONFIRM: [
                CallbackQueryHandler(remove_currency_confirm, pattern='^confirm_remove_currency$'),
                CallbackQueryHandler(back_to_currencies, pattern='^cancel_remove_currency$'),
            ],
            
            # Состояния для управления банками
            BANK_MENU: [
                CallbackQueryHandler(add_bank_name, pattern='^add_bank$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                CallbackQueryHandler(remove_bank, pattern='^bank_\d+$'),
            ],
            ADD_BANK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_bank_details),
            ],
            ADD_BANK_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_bank),
            ],
            REMOVE_BANK_CONFIRM: [
                CallbackQueryHandler(remove_bank_confirm, pattern='^confirm_remove_bank$'),
                CallbackQueryHandler(back_to_banks, pattern='^cancel_remove_bank$'),
            ],
            
            # Состояния для управления методами оплаты
            PAYMENT_METHOD_MENU: [
                CallbackQueryHandler(add_payment_method_name, pattern='^add_payment_method$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                CallbackQueryHandler(remove_payment_method, pattern='^payment_method_\d+$'),
            ],
            ADD_PAYMENT_METHOD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_payment_method_details),
            ],
            ADD_PAYMENT_METHOD_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_payment_method),
            ],
            REMOVE_PAYMENT_METHOD_CONFIRM: [
                CallbackQueryHandler(remove_payment_method_confirm, pattern='^confirm_remove_payment_method$'),
                CallbackQueryHandler(back_to_payment_methods, pattern='^cancel_remove_payment_method$'),
            ],
            
            # Состояния для управления комиссиями
            COMMISSION_MENU: [
                CallbackQueryHandler(add_commission_select_pair, pattern='^add_commission$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                CallbackQueryHandler(remove_commission, pattern='^commission_\d+$'),
            ],
            SELECT_COMMISSION_PAIR: [
                CallbackQueryHandler(input_commission_value, pattern='^commission_pair_\w+/\w+$'),
                CallbackQueryHandler(back_to_commissions, pattern='^back_to_commissions$'),
            ],
            INPUT_COMMISSION_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_commission),
            ],
            
            # Состояния для управления менеджерами
            MANAGER_MENU: [
                CallbackQueryHandler(add_manager_user_id, pattern='^add_manager$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                CallbackQueryHandler(remove_manager, pattern='^manager_\d+$'),
            ],
            ADD_MANAGER_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_manager),
            ],
            REMOVE_MANAGER_CONFIRM: [
                CallbackQueryHandler(remove_manager_confirm, pattern='^confirm_remove_manager$'),
                CallbackQueryHandler(back_to_managers, pattern='^cancel_remove_manager$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
    
    dispatcher.add_handler(admin_conv_handler)