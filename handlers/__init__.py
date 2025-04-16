# handlers/__init__.py
from . import user, profile, support

# Функция для регистрации всех обработчиков
def setup_handlers(dp):
    user.setup(dp)
    # exchange.setup(dp)
    # orders.setup(dp)
    profile.setup(dp)
    support.setup(dp)
    # manager.setup(dp)
    # admin.setup(dp)