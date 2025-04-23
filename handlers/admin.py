from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from keyboards.reply import get_admin_keyboard, get_main_keyboard
from states.admin import AdminStates
from utils.error_handler import handle_errors
from database.models import User, UserRole, Currency, Bank, ExchangeRate, CurrencyType
from utils import logger

router = Router()

# Middleware to check if user is admin
async def admin_filter(message: types.Message, db_user: dict):
    """Check if the user is an admin"""
    if db_user['telegram_id'] not in ADMIN_IDS and db_user['role'] != UserRole.ADMIN:
        await message.answer("У вас немає доступу до цієї команди.")
        return False
    return True

# Admin panel
@router.message(F.text == "⚙️ Налаштування")
@handle_errors
async def admin_settings(message: types.Message, db_user: dict):
    """Admin settings menu"""
    if not await admin_filter(message, db_user):
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="💱 Керування курсами валют", callback_data="admin:rates")
    )
    builder.row(
        types.InlineKeyboardButton(text="👥 Керування менеджерами", callback_data="admin:managers")
    )
    builder.row(
        types.InlineKeyboardButton(text="🏦 Банки", callback_data="admin:banks"),
        types.InlineKeyboardButton(text="💰 Валюти", callback_data="admin:currencies")
    )
    builder.row(
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")
    )
    
    await message.answer(
        "⚙️ <b>Адміністративна панель</b>\n\n"
        "Оберіть розділ для керування:",
        reply_markup=builder.as_markup()
    )

# Exchange rates management
@router.callback_query(F.data == "admin:rates")
@handle_errors
async def manage_rates(callback: types.CallbackQuery, db_user: dict, session):
    """Exchange rates management"""
    if callback.from_user.id not in ADMIN_IDS and db_user['role'] != UserRole.ADMIN:
        await callback.answer("У вас немає доступу до цієї функції", show_alert=True)
        return
    
    rates = session.query(ExchangeRate).all()
    
    text = "💱 <b>Керування курсами валют</b>\n\n"
    
    if not rates:
        text += "Курси валют не налаштовані."
    else:
        for rate in rates:
            from_curr = session.query(Currency).filter_by(id=rate.from_currency_id).first()
            to_curr = session.query(Currency).filter_by(id=rate.to_currency_id).first()
            if from_curr and to_curr:
                text += f"{from_curr.code} → {to_curr.code}: {rate.rate:.4f}\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="➕ Додати курс", callback_data="admin:rates:add")
    )
    builder.row(
        types.InlineKeyboardButton(text="🔄 Оновити курс", callback_data="admin:rates:update")
    )
    builder.row(
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "admin:rates:add")
@handle_errors
async def add_rate(callback: types.CallbackQuery, state: FSMContext, session):
    """Start adding a new exchange rate"""
    currencies = session.query(Currency).filter_by(enabled=True).all()
    
    if len(currencies) < 2:
        await callback.message.edit_text(
            "❌ Для додавання курсу потрібно мати хоча б дві валюти в системі.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
            ).as_markup()
        )
        return
    
    builder = InlineKeyboardBuilder()
    for currency in currencies:
        builder.row(
            types.InlineKeyboardButton(
                text=f"{currency.code} ({CurrencyType(currency.type).name.lower()})",
                callback_data=f"admin:rate:from:{currency.id}"
            )
        )
    builder.row(
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
    )
    
    await callback.message.edit_text(
        "💱 <b>Додавання курсу обміну</b>\n\n"
        "Оберіть першу валюту пари обміну:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(AdminStates.UPDATE_RATE_SELECT_PAIR)
    await callback.answer()

@router.callback_query(F.data.startswith("admin:rate:from:"), AdminStates.UPDATE_RATE_SELECT_PAIR)
@handle_errors
async def select_to_currency(callback: types.CallbackQuery, state: FSMContext, session):
    """Select second currency for the rate pair"""
    from_currency_id = int(callback.data.split(":")[-1])
    from_currency = session.query(Currency).filter_by(id=from_currency_id).first()
    
    if not from_currency:
        await callback.message.edit_text(
            "❌ Валюту не знайдено. Спробуйте знову.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
            ).as_markup()
        )
        return
    
    await state.update_data(from_currency_id=from_currency_id)
    
    currencies = session.query(Currency).filter_by(enabled=True).all()
    
    builder = InlineKeyboardBuilder()
    for currency in currencies:
        if currency.id != from_currency_id:
            builder.row(
                types.InlineKeyboardButton(
                    text=f"{currency.code} ({CurrencyType(currency.type).name.lower()})",
                    callback_data=f"admin:rate:to:{currency.id}"
                )
            )
    builder.row(
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates:add")
    )
    
    await callback.message.edit_text(
        f"💱 <b>Додавання курсу обміну</b>\n\n"
        f"Перша валюта: {from_currency.code}\n"
        f"Оберіть другу валюту пари обміну:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("admin:rate:to:"), AdminStates.UPDATE_RATE_SELECT_PAIR)
@handle_errors
async def enter_rate_value(callback: types.CallbackQuery, state: FSMContext, session):
    """Ask for the rate value"""
    to_currency_id = int(callback.data.split(":")[-1])
    to_currency = session.query(Currency).filter_by(id=to_currency_id).first()
    
    if not to_currency:
        await callback.message.edit_text(
            "❌ Валюту не знайдено. Спробуйте знову.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
            ).as_markup()
        )
        return
    
    data = await state.get_data()
    from_currency_id = data.get("from_currency_id")
    from_currency = session.query(Currency).filter_by(id=from_currency_id).first()
    
    await state.update_data(to_currency_id=to_currency_id)
    
    # Check if the rate already exists
    existing_rate = session.query(ExchangeRate).filter_by(
        from_currency_id=from_currency_id,
        to_currency_id=to_currency_id
    ).first()
    
    if existing_rate:
        await callback.message.edit_text(
            f"❌ Курс обміну {from_currency.code} → {to_currency.code} вже існує.\n"
            f"Поточне значення: {existing_rate.rate:.4f}\n\n"
            f"Для оновлення використовуйте функцію 'Оновити курс'.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
            ).as_markup()
        )
        await state.clear()
        return
    
    await callback.message.edit_text(
        f"💱 <b>Додавання курсу обміну</b>\n\n"
        f"Пара: {from_currency.code} → {to_currency.code}\n"
        f"Введіть значення курсу (скільки {to_currency.code} за 1 {from_currency.code}):",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
        ).as_markup()
    )
    
    await state.set_state(AdminStates.UPDATE_RATE_ENTER_VALUE)
    await callback.answer()

@router.message(AdminStates.UPDATE_RATE_ENTER_VALUE)
@handle_errors
async def save_rate_value(message: types.Message, state: FSMContext, session):
    """Save the new exchange rate"""
    try:
        rate_value = float(message.text.replace(',', '.'))
        if rate_value <= 0:
            await message.answer("❌ Курс має бути більше нуля. Спробуйте знову.")
            return
    except ValueError:
        await message.answer("❌ Невірний формат. Введіть число (наприклад, 38.5).")
        return
    
    data = await state.get_data()
    from_currency_id = data.get("from_currency")
    to_currency_id = data.get("to_currency")
    
    from_currency = session.query(Currency).filter_by(id=from_currency_id).first()
    to_currency = session.query(Currency).filter_by(id=to_currency_id).first()
    
    if not from_currency or not to_currency:
        await message.answer("❌ Помилка при отриманні даних про валюти.")
        await state.clear()
        return
    
    # Create new exchange rate
    new_rate = ExchangeRate(
        from_currency_id=from_currency_id,
        to_currency_id=to_currency_id,
        rate=rate_value
    )
    
    session.add(new_rate)
    
    # Also add reverse rate automatically (e.g., if adding USD→UAH, also add UAH→USD)
    reverse_rate = ExchangeRate(
        from_currency_id=to_currency_id,
        to_currency_id=from_currency_id,
        rate=1/rate_value
    )
    
    session.add(reverse_rate)
    session.commit()
    
    await message.answer(
        f"✅ Курс обміну додано успішно!\n\n"
        f"{from_currency.code} → {to_currency.code}: {rate_value:.4f}\n"
        f"{to_currency.code} → {from_currency.code}: {(1/rate_value):.4f}",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="◀️ Назад до курсів", callback_data="admin:rates")
        ).as_markup()
    )
    
    await state.clear()

@router.callback_query(F.data == "admin:rates:update")
@handle_errors
async def update_rate(callback: types.CallbackQuery, state: FSMContext, session):
    """Select rate to update"""
    rates = session.query(ExchangeRate).all()
    
    if not rates:
        await callback.message.edit_text(
            "❌ Немає курсів для оновлення. Спочатку додайте курси.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
            ).as_markup()
        )
        return
    
    builder = InlineKeyboardBuilder()
    
    for rate in rates:
        from_currency = session.query(Currency).filter_by(id=rate.from_currency_id).first()
        to_currency = session.query(Currency).filter_by(id=rate.to_currency_id).first()
        
        if from_currency and to_currency:
            builder.row(
                types.InlineKeyboardButton(
                    text=f"{from_currency.code} → {to_currency.code} ({rate.rate:.4f})",
                    callback_data=f"admin:rate:update:{rate.id}"
                )
            )
    
    builder.row(
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
    )
    
    await callback.message.edit_text(
        "🔄 <b>Оновлення курсу обміну</b>\n\n"
        "Оберіть курс для оновлення:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("admin:rate:update:"))
@handle_errors
async def enter_updated_rate(callback: types.CallbackQuery, state: FSMContext, session):
    """Ask for the new rate value"""
    rate_id = int(callback.data.split(":")[-1])
    rate = session.query(ExchangeRate).filter_by(id=rate_id).first()
    
    if not rate:
        await callback.message.edit_text(
            "❌ Курс не знайдено. Спробуйте знову.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:rates")
            ).as_markup()
        )
        return
    
    from_currency = session.query(Currency).filter_by(id=rate.from_currency_id).first()
    to_currency = session.query(Currency).filter_by(id=rate.to_currency_id).first()
    
    await state.update_data(rate_id=rate_id)
    
    await callback.message.edit_text(
        f"🔄 <b>Оновлення курсу обміну</b>\n\n"
        f"Пара: {from_currency.code} → {to_currency.code}\n"
        f"Поточне значення: {rate.rate:.4f}\n\n"
        f"Введіть нове значення курсу (скільки {to_currency.code} за 1 {from_currency.code}):",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="◀️ Скасувати", callback_data="admin:rates")
        ).as_markup()
    )
    
    await state.set_state(AdminStates.UPDATE_RATE_ENTER_VALUE)
    await callback.answer()

# Manager management
@router.callback_query(F.data == "admin:managers")
@handle_errors
async def manage_managers(callback: types.CallbackQuery, db_user: dict, session):
    """Manager management"""
    if callback.from_user.id not in ADMIN_IDS and db_user['role'] != UserRole.ADMIN:
        await callback.answer("У вас немає доступу до цієї функції", show_alert=True)
        return
    
    managers = session.query(User).filter_by(role=UserRole.MANAGER).all()
    
    text = "👥 <b>Керування менеджерами</b>\n\n"
    
    if not managers:
        text += "В системі немає менеджерів."
    else:
        for i, manager in enumerate(managers, 1):
            text += f"{i}. {manager.first_name or ''} {manager.last_name or ''} "
            if manager.username:
                text += f"(@{manager.username})"
            text += f" [ID: {manager.telegram_id}]\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="➕ Додати менеджера", callback_data="admin:manager:add")
    )
    if managers:
        builder.row(
            types.InlineKeyboardButton(text="➖ Видалити менеджера", callback_data="admin:manager:remove")
        )
    builder.row(
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "admin:manager:add")
@handle_errors
async def add_manager_start(callback: types.CallbackQuery, state: FSMContext):
    """Start adding a new manager"""
    await callback.message.edit_text(
        "👤 <b>Додавання нового менеджера</b>\n\n"
        "Введіть Telegram ID користувача, якого потрібно призначити менеджером:",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="◀️ Скасувати", callback_data="admin:managers")
        ).as_markup()
    )
    
    await state.set_state(AdminStates.ADD_MANAGER)
    await callback.answer()

@router.message(AdminStates.ADD_MANAGER)
@handle_errors
async def add_manager_process(message: types.Message, state: FSMContext, session):
    """Process adding a new manager"""
    try:
        manager_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Невірний формат ID. Введіть числовий Telegram ID.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Скасувати", callback_data="admin:managers")
            ).as_markup()
        )
        return
    
    # Check if user exists
    user = session.query(User).filter_by(telegram_id=manager_id).first()
    
    if user and user.role == UserRole.MANAGER:
        await message.answer(
            "❌ Цей користувач вже є менеджером.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:managers")
            ).as_markup()
        )
        await state.clear()
        return
    
    if user:
        user.role = UserRole.MANAGER
        success_text = f"✅ Користувача {user.first_name or ''} {user.last_name or ''} призначено менеджером."
    else:
        new_manager = User(telegram_id=manager_id, role=UserRole.MANAGER)
        session.add(new_manager)
        success_text = f"✅ Користувача з ID {manager_id} додано як менеджера. Їм потрібно буде запустити бота, щоб їхні дані оновилися."
    
    session.commit()
    
    await message.answer(
        success_text,
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:managers")
        ).as_markup()
    )
    
    # Try to notify the new manager
    if user:
        try:
            await message.bot.send_message(
                manager_id,
                "🔔 Вас призначено менеджером обмінника. Тепер вам доступні додаткові функції."
            )
        except Exception as e:
            logger.error(f"Failed to notify new manager: {e}")
    
    await state.clear()

@router.callback_query(F.data == "admin:manager:remove")
@handle_errors
async def remove_manager_start(callback: types.CallbackQuery, state: FSMContext, session):
    """Start removing a manager"""
    managers = session.query(User).filter_by(role=UserRole.MANAGER).all()
    
    if not managers:
        await callback.message.edit_text(
            "❌ В системі немає менеджерів для видалення.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:managers")
            ).as_markup()
        )
        return
    
    builder = InlineKeyboardBuilder()
    
    for manager in managers:
        name = f"{manager.first_name or ''} {manager.last_name or ''}"
        if manager.username:
            name += f" (@{manager.username})"
        
        builder.row(
            types.InlineKeyboardButton(
                text=name,
                callback_data=f"admin:manager:remove:{manager.telegram_id}"
            )
        )
    
    builder.row(
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:managers")
    )
    
    await callback.message.edit_text(
        "👤 <b>Видалення менеджера</b>\n\n"
        "Оберіть менеджера, якого потрібно видалити:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("admin:manager:remove:"))
@handle_errors
async def remove_manager_confirm(callback: types.CallbackQuery, state: FSMContext, session):
    """Confirm removing a manager"""
    manager_id = int(callback.data.split(":")[-1])
    
    manager = session.query(User).filter_by(telegram_id=manager_id).first()
    
    if not manager or manager.role != UserRole.MANAGER:
        await callback.message.edit_text(
            "❌ Менеджера не знайдено. Можливо, він вже був видалений.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:managers")
            ).as_markup()
        )
        return
    
    name = f"{manager.first_name or ''} {manager.last_name or ''}"
    if manager.username:
        name += f" (@{manager.username})"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="✅ Так, видалити",
            callback_data=f"admin:manager:remove:confirm:{manager_id}"
        )
    )
    builder.row(
        types.InlineKeyboardButton(text="❌ Скасувати", callback_data="admin:managers")
    )
    
    await callback.message.edit_text(
        f"❓ <b>Підтвердження дії</b>\n\n"
        f"Ви дійсно хочете видалити менеджера {name}?",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("admin:manager:remove:confirm:"))
@handle_errors
async def remove_manager_process(callback: types.CallbackQuery, state: FSMContext, session):
    """Process removing a manager"""
    manager_id = int(callback.data.split(":")[-1])
    
    manager = session.query(User).filter_by(telegram_id=manager_id).first()
    
    if not manager or manager.role != UserRole.MANAGER:
        await callback.message.edit_text(
            "❌ Менеджера не знайдено. Можливо, він вже був видалений.",
            reply_markup=InlineKeyboardBuilder().row(
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:managers")
            ).as_markup()
        )
        return
    
    # Change role back to regular user
    manager.role = UserRole.USER
    session.commit()
    
    name = f"{manager.first_name or ''} {manager.last_name or ''}"
    if manager.username:
        name += f" (@{manager.username})"
    
    await callback.message.edit_text(
        f"✅ Менеджера {name} видалено. Користувач тепер має роль звичайного користувача.",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:managers")
        ).as_markup()
    )
    
    # Try to notify the former manager
    try:
        await callback.bot.send_message(
            manager_id,
            "🔔 Вас було видалено з ролі менеджера обмінника."
        )
    except Exception as e:
        logger.error(f"Failed to notify former manager: {e}")
    
    await callback.answer()

# Currency management
@router.callback_query(F.data == "admin:currencies")
@handle_errors
async def manage_currencies(callback: types.CallbackQuery, db_user: dict, session):
    """Currency management"""
    if callback.from_user.id not in ADMIN_IDS and db_user['role'] != UserRole.ADMIN:
        await callback.answer("У вас немає доступу до цієї функції", show_alert=True)
        return
    
    currencies = session.query(Currency).all()
    
    text = "💰 <b>Керування валютами</b>\n\n"
    
    if not currencies:
        text += "В системі немає валют."
    else:
        text += "<b>Активні валюти:</b>\n"
        for currency in currencies:
            if currency.enabled:
                text += f"• {currency.code} - {currency.name} ({CurrencyType(currency.type).name.lower()})\n"
        
        text += "\n<b>Неактивні валюти:</b>\n"
        inactive = False
        for currency in currencies:
            if not currency.enabled:
                text += f"• {currency.code} - {currency.name} ({CurrencyType(currency.type).name.lower()})\n"
                inactive = True
        
        if not inactive:
            text += "Немає неактивних валют\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="➕ Додати валюту", callback_data="admin:currency:add")
    )
    if currencies:
        builder.row(
            types.InlineKeyboardButton(text="✅ Активувати/Деактивувати", callback_data="admin:currency:toggle")
        )
    builder.row(
        types.InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "admin:currency:add")
@handle_errors
async def add_currency_start(callback: types.CallbackQuery, state: FSMContext):
    """Start adding a new currency"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="CRYPTO", callback_data="admin:currency:type:CRYPTO")
    )
    builder.row(
        types.InlineKeyboardButton(text="FIAT", callback_data="admin:currency:type:FIAT")
    )
    builder.row(
        types.InlineKeyboardButton(text="◀️ Скасувати", callback_data="admin:currencies")
    )
    
    await callback.message.edit_text(
        "💰 <b>Додавання нової валюти</b>\n\n"
        "Виберіть тип валюти:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("admin:currency:type:"))
@handle_errors
async def add_currency_code(callback: types.CallbackQuery, state: FSMContext):
    """Ask for currency code"""
    currency_type = callback.data.split(":")[-1]
    
    await state.update_data(currency_type=currency_type)
    await state.set_state(AdminStates.ADD_CURRENCY)
    
    await callback.message.edit_text(
        f"💰 <b>Додавання нової валюти</b>\n\n"
        f"Тип: {currency_type}\n\n"
        f"Введіть код валюти (наприклад, USD або BTC):",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="◀️ Скасувати", callback_data="admin:currencies")
        ).as_markup()
    )
    
    await callback.answer()

def setup(dp):
    dp.include_router(router)