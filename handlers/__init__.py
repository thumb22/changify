from . import user, profile, support
def setup_handlers(dp):
    user.setup(dp)
    profile.setup(dp)
    support.setup(dp)
    # exchange.setup(dp)
    # orders.setup(dp)
    # manager.setup(dp)
    # admin.setup(dp)