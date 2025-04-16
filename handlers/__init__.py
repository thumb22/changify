from . import user, profile, support, orders, exchange
def setup_handlers(dp):
    user.setup(dp)
    profile.setup(dp)
    support.setup(dp)
    orders.setup(dp)
    exchange.setup(dp)