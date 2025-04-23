from aiogram.fsm.state import State, StatesGroup

class ExchangeStates(StatesGroup):
    """Состояния для создания заявки на обмен"""
    SELECT_FROM_CURRENCY = State()
    SELECT_TO_CURRENCY = State()
    ENTER_AMOUNT = State()
    SELECT_BANK = State()
    ENTER_PAYMENT_DETAILS = State()
    CONFIRM_ORDER = State()