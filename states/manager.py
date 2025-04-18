from aiogram.fsm.state import StatesGroup, State

class ManagerStates(StatesGroup):
    viewing_orders = State()
    accepting_order = State()
    awaiting_payment = State()
    confirming_payment = State()
    completing_order = State()
    rejecting_order = State()
    awaiting_rejection_comment = State()
    awaiting_payment_details = State()
    replying_to_user = State()
