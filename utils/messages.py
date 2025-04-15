
WELCOME_MESSAGE = """
👋 Вітаємо у Changify - боті для P2P-обміну криптовалют та фіатних валют!

Оберіть дію із меню, щоб почати.
"""

HELP_MESSAGE = """
📚 <b>Основні команди бота:</b>

/start - почати роботу з ботом
/help - показати цю довідку
/rates - поточні курси обміну
/profile - інформація про ваш профіль
/history - історія ваших заявок

Якщо у вас виникли питання, зверніться до адміністратора бота.
"""

ERROR_MESSAGE = "❌ Сталася помилка. Будь ласка, спробуйте ще раз або зв'яжіться з адміністратором."

# Сообщения для работы с курсами валют
RATES_MESSAGE = """
📊 <b>Поточні курси обміну:</b>

{rates}

Курси оновлено: {updated_at}
"""

RATE_ITEM_TEMPLATE = "{from_code} ➡️ {to_code}: {rate} {to_symbol}"

# Сообщения для создания заявок
EXCHANGE_START_MESSAGE = "🔄 Оберіть валюту, яку ви хочете обміняти:"
EXCHANGE_TO_MESSAGE = "🔄 Оберіть валюту, на яку ви хочете обміняти {from_currency}:"
EXCHANGE_AMOUNT_MESSAGE = "💰 Введіть суму {currency}, яку ви хочете обміняти:"
EXCHANGE_BANK_MESSAGE = "🏦 Оберіть банк для отримання коштів:"
EXCHANGE_PAYMENT_DETAILS_MESSAGE = "📝 Введіть реквізити для отримання коштів:"
EXCHANGE_CONFIRM_MESSAGE = """
📋 <b>Перевірте деталі вашої заявки:</b>

Обмін: {amount_from} {from_currency} ➡️ {amount_to} {to_currency}
Курс: 1 {from_currency} = {rate} {to_currency}
{bank_info}

Натисніть "✅ Підтвердити" для створення заявки або "❌ Скасувати" для скасування.
"""

EXCHANGE_SUCCESS_MESSAGE = """
✅ <b>Заявка успішно створена!</b>

Номер заявки: #{order_id}
Обмін: {amount_from} {from_currency} ➡️ {amount_to} {to_currency}

{payment_instructions}

Після здійснення оплати натисніть "💰 Я оплатив".
"""

# Сообщения для работы с заявками
ORDER_AWAITING_PAYMENT = """
⏳ <b>Очікуємо оплату для заявки #{order_id}</b>

Відправте {amount_from} {from_currency} за реквізитами:
{payment_details}

Після оплати натисніть "💰 Я оплатив".
"""

ORDER_PAYMENT_CONFIRMED = """
✅ <b>Оплату для заявки #{order_id} підтверджено</b>

Очікуйте перевірки менеджером. Це може зайняти деякий час.
"""

ORDER_COMPLETED = """
🎉 <b>Заявку #{order_id} успішно виконано!</b>

Обмін {amount_from} {from_currency} ➡️ {amount_to} {to_currency} завершено.
Дякуємо за використання нашого сервісу!
"""

ORDER_CANCELLED = """
❌ <b>Заявку #{order_id} скасовано</b>

Причина: {reason}
"""

# Сообщения для менеджеров
MANAGER_NEW_ORDER = """
🔔 <b>Нова заявка #{order_id}</b>

Користувач: {user_name} (@{username})
Обмін: {amount_from} {from_currency} ➡️ {amount_to} {to_currency}
Курс: 1 {from_currency} = {rate} {to_currency}
{bank_info}
Статус: {status}
"""

MANAGER_PAYMENT_CONFIRMED = """
💰 <b>Користувач підтвердив оплату для заявки #{order_id}</b>

Перевірте надходження коштів і підтвердіть або відхиліть заявку.
"""

# Сообщения для администраторов
ADMIN_RATE_UPDATE_MESSAGE = """
💱 <b>Оновлення курсу валют</b>

Оберіть пару валют для оновлення:
"""

ADMIN_RATE_SET_MESSAGE = "Введіть новий курс для пари {from_currency} ➡️ {to_currency}:"
ADMIN_RATE_UPDATED_MESSAGE = "✅ Курс {from_currency} ➡️ {to_currency} оновлено до {rate}"

# Сообщения для профиля
PROFILE_MESSAGE = """
👤 <b>Профіль користувача</b>

ID: {user_id}
Ім'я: {first_name} {last_name}
Username: @{username}
Роль: {role}
Дата реєстрації: {created_at}
Кількість заявок: {orders_count}
"""

# Сообщения для истории заявок
HISTORY_EMPTY_MESSAGE = "📋 У вас поки що немає заявок на обмін."
HISTORY_MESSAGE = "📋 <b>Історія ваших заявок:</b>"
HISTORY_ITEM_TEMPLATE = """
#{order_id}: {amount_from} {from_currency} ➡️ {amount_to} {to_currency}
Статус: {status}
Дата: {created_at}
"""

# Статусы заявок на украинском
ORDER_STATUS = {
    "created": "Створено",
    "awaiting_payment": "Очікує оплати",
    "payment_confirmed": "Оплату підтверджено",
    "processing": "Обробляється",
    "completed": "Завершено",
    "cancelled": "Скасовано"
}