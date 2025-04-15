# database/__init__.py
from .models import (
    Base, User, UserRole, Currency, CurrencyType, 
    Bank, ExchangeRate, Order, OrderStatus, Setting, AuditLog
)
from .db_operations import (
    get_engine, init_db, get_session, 
    setup_initial_data, create_admin_user, get_or_create_user
)

# Этот файл делает все модели и функции доступными при импорте пакета database