# states/support.py
from aiogram.fsm.state import State, StatesGroup

class SupportStates(StatesGroup):
    MAIN = State()
    SENDING_MESSAGE = State()
    ACTIVE_CHAT = State()