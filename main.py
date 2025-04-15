import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database.db_operations import get_engine, init_db, get_session, setup_initial_data
from database.models import User, UserRole

logging.basicConfig(
    level=config.LOG_LEVELS.get(config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE,
    filemode='a'
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

engine = get_engine(config.DATABASE_URL)
init_db(engine)
db_session = get_session(engine)
setup_initial_data(db_session)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        user_data = {
            'telegram_id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }
        
        session = get_session(engine)
        from database.db_operations import get_or_create_user
        user = get_or_create_user(session, user_data)
        session.close()
        
        await message.answer(
            f"👋 Привіт, {message.from_user.first_name}!\n\n"
            f"Ласкаво просимо до Changify - бота для P2P-обміну криптовалют та фіатних валют.\n\n"
            f"Щоб почати, оберіть потрібну дію в меню."
        )
        
    except Exception as e:
        logger.error(f"Помилка в обробнику /start: {e}")
        await message.answer("Сталася помилка. Спробуйте ще раз пізніше.")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📚 <b>Основні команди бота:</b>\n\n"
        "/start - почати роботу з ботом\n"
        "/help - показати цю довідку\n"
        "/rates - поточні курси обміну\n"
        "/profile - інформація про ваш профіль\n"
        "/history - історія ваших заявок\n\n"
        "Якщо у вас виникли питання, зверніться до адміністратора бота."
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message()
async def unknown_message(message: types.Message):
    """Обробник невідомих повідомлень"""
    await message.answer("Я не розумію цю команду. Використовуйте /help для перегляду доступних команд.")


async def on_startup():
    """Дії при запуску бота"""
    logger.info("Бот запущений")
    
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
    """Дії при зупинці бота"""
    logger.info("Бот зупинений")
    if db_session:
        db_session.close()


async def main():
    """Основна функція запуску бота"""
    try:
        await on_startup()
        await dp.start_polling(bot)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинений користувачем")
    except Exception as e:
        logger.critical(f"Непередбачена помилка: {e}")
        raise