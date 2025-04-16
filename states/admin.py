from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    """Состояния для админских функций"""
    UPDATE_RATE_SELECT_PAIR = State()  # Выбор пары валют для обновления курса
    UPDATE_RATE_ENTER_VALUE = State()  # Ввод нового значения курса
    
    ADD_MANAGER = State()              # Добавление менеджера
    REMOVE_MANAGER = State()           # Удаление менеджера
    
    ADD_CURRENCY = State()             # Добавление новой валюты
    ADD_BANK = State()                 # Добавление нового банка