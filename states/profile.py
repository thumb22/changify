from aiogram.fsm.state import State, StatesGroup

class ProfileStates(StatesGroup):
    EDIT_CONTACTS = State()