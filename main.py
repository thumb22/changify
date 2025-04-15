# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database.db_operations import get_engine, init_db, get_session, setup_initial_data
from database.models import User, UserRole

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVELS.get(config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE,
    filemode='a'
)
logger = logging.getLogger(__name__)

# Настройка бота
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
engine = get_engine(config.DATABASE_URL)
init_db(engine)
db_session = get_session(engine)
setup_initial_data(db_session)


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        user_data = {
            'telegram_id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'language_code': message.from_user.language_code or config.DEFAULT_LANGUAGE
        }
        
        session = get_session(engine)
        from database.db_operations import get_or_create_user
        user = get_or_create_user(session, user_data)
        session.close()
        
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"Добро пожаловать в Changify - бот для P2P-обмена криптовалют и фиатных валют.\n\n"
            f"Чтобы начать работу, выберите нужное действие в меню."
        )
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз позже.")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📚 <b>Основные команды бота:</b>\n\n"
        "/start - начать работу с ботом\n"
        "/help - показать эту справку\n"
        "/rates - текущие курсы обмена\n"
        "/profile - информация о вашем профиле\n"
        "/history - история ваших заявок\n\n"
        "Если у вас возникли вопросы, обратитесь к администратору бота."
    )
    await message.answer(help_text, parse_mode="HTML")


# Обработчик неизвестных команд
@dp.message()
async def unknown_message(message: types.Message):
    """Обработчик неизвестных сообщений"""
    await message.answer("Я не понимаю эту команду. Используйте /help для получения списка доступных команд.")


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запущен")
    
    # Создаем администраторов из конфигурации
    session = get_session(engine)
    for admin_id in config.ADMIN_IDS:
        from database.db_operations import create_admin_user
        create_admin_user(session, admin_id)
    
    # Создаем менеджеров из конфигурации
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
    """Действия при остановке бота"""
    logger.info("Бот остановлен")
    if db_session:
        db_session.close()


async def main():
    """Основная функция запуска бота"""
    try:
        # Регистрируем хэндлеры из других модулей
        # Этот блок будет расширен по мере добавления обработчиков

        # Выполняем действия при запуске
        await on_startup()
        
        # Запускаем поллинг
        await dp.start_polling(bot)
    finally:
        # Выполняем действия при остановке
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Необработанная ошибка: {e}")
        raise