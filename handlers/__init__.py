from . import user, profile, support, orders, exchange, manager
def setup_handlers(dp):
    user.setup(dp)
    profile.setup(dp)
    support.setup(dp)
    orders.setup(dp)
    exchange.setup(dp)
    manager.setup(dp)