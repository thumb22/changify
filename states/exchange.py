# states/exchange.py
from aiogram.fsm.state import State, StatesGroup

class ExchangeStates(StatesGroup):
    """Состояния для создания заявки на обмен"""
    SELECT_FROM_CURRENCY = State()  # Выбор исходной валюты
    SELECT_TO_CURRENCY = State()    # Выбор целевой валюты
    ENTER_AMOUNT = State()          # Ввод суммы для обмена
    SELECT_BANK = State()           # Выбор банка (для UAH)
    ENTER_PAYMENT_DETAILS = State() # Ввод реквизитов для платежа
    CONFIRM_ORDER = State()         # Подтверждение заявки