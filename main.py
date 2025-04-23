import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
from database.db_operations import get_engine, init_db, get_session, setup_initial_data
from database.models import User, UserRole
from keyboards.reply import get_main_keyboard, get_manager_keyboard, get_admin_keyboard
from middlewares.user_middleware import UserMiddleware
from utils.logger import setup_logger
from utils.error_handler import handle_errors
from handlers import setup_handlers

logger = setup_logger(__name__)

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

fallback_router = Router()

engine = get_engine(config.DATABASE_URL)
init_db(engine)
db_session = get_session(engine)
setup_initial_data(db_session)
db_session.close()

dp.message.middleware(UserMiddleware(engine))
dp.callback_query.middleware(UserMiddleware(engine))

@dp.message(Command("start"))
@handle_errors
async def cmd_start(message: types.Message, db_user: dict):
    if db_user['role'] == UserRole.ADMIN:
        keyboard = get_admin_keyboard()
    elif db_user['role'] == UserRole.MANAGER:
        keyboard = get_manager_keyboard()
    else:
        keyboard = get_main_keyboard()
    await message.answer(
        f"👋 Привіт, {message.from_user.first_name}!\n\n"
        f"Ласкаво просимо до Changify - бота для P2P-обміну криптовалют та фіатних валют.\n\n"
        f"Щоб почати, оберіть потрібну дію в меню.",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
@handle_errors
async def cmd_help(message: types.Message):
    help_text = (
        "📚 <b>Основні команди бота:</b>\n\n"
        "/start - почати роботу з ботом\n"
        "/help - показати цю довідку\n"
        "Якщо у вас виникли питання, зверніться до адміністратора бота."
    )
    await message.answer(help_text)

async def on_startup():
    logger.info("Bot started")
    session = get_session(engine)
    for admin_id in config.ADMIN_IDS:
        from database.db_operations import create_admin_user
        create_admin_user(session, admin_id)
    for manager_id in config.MANAGER_IDS:
        user = session.query(User).filter_by(telegram_id=manager_id).first()
        if user:
            user.role = UserRole.MANAGER
        else:
            new_manager = User(telegram_id=manager_id, role=UserRole.MANAGER)
            session.add(new_manager)
    session.commit()
    session.close()

async def on_shutdown():
    logger.info("Bot stopped")

async def main():
    try:
        await on_startup()
        setup_handlers(dp)
        await dp.start_polling(bot)
    finally:
        await on_shutdown()
        

@fallback_router.message()
@handle_errors
async def unknown_message(message: types.Message):
    await message.answer("Я не розумію цю команду. Використовуйте /help для перегляду доступних команд.")

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning("Event loop is already running, skipping main()")
        else:
            asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}")
        raise