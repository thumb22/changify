# states/profile.py
from aiogram.fsm.state import State, StatesGroup

class ProfileStates(StatesGroup):
    """Состояния для настройки профиля"""
    EDIT_CONTACTS = State()