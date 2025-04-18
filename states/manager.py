from aiogram.fsm.state import StatesGroup, State

class ManagerStates(StatesGroup):
    viewing_orders = State()            # Просмотр активных заявок
    accepting_order = State()           # Прийняття заявки
    awaiting_payment = State()          # Очікування оплати
    confirming_payment = State()        # Підтвердження оплати
    completing_order = State()          # Завершення заявки
    rejecting_order = State()           # Відхилення заявки
    replying_to_user = State()          # Відповідь на повідомлення користувача
