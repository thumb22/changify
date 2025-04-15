from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging

from .models import Base, Currency, CurrencyType, Bank, User, UserRole, Setting

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_engine(db_url="sqlite:///changify.db"):
    """Создает и возвращает движок SQLAlchemy"""
    return create_engine(db_url, echo=False)

def init_db(engine):
    """Инициализирует базу данных и создает таблицы"""
    Base.metadata.create_all(engine)
    logger.info("База данных инициализирована")

def get_session(engine):
    """Создает и возвращает сессию SQLAlchemy"""
    Session = sessionmaker(bind=engine)
    return Session()

def setup_initial_data(session):
    """Заполняет базу данных начальными данными"""
    try:
        # Добавляем валюты
        if session.query(Currency).count() == 0:
            currencies = [
                Currency(code="USDT", name="Tether", type=CurrencyType.CRYPTO),
                Currency(code="USD", name="US Dollar", type=CurrencyType.FIAT),
                Currency(code="UAH", name="Ukrainian Hryvnia", type=CurrencyType.FIAT)
            ]
            session.add_all(currencies)
            session.commit()
            logger.info("Добавлены начальные валюты")
        
        # Получаем ID валюты UAH для создания банков
        uah = session.query(Currency).filter_by(code="UAH").first()
        
        # Добавляем банки для UAH
        if uah and session.query(Bank).count() == 0:
            banks = [
                Bank(name="ПриватБанк", currency_id=uah.id),
                Bank(name="Монобанк", currency_id=uah.id),
                Bank(name="ПУМБ", currency_id=uah.id)
            ]
            session.add_all(banks)
            session.commit()
            logger.info("Добавлены начальные банки")
        
        # Добавляем начальные настройки
        if session.query(Setting).count() == 0:
            settings = [
                Setting(key="bot_name", value="Changify", description="Название бота"),
                Setting(key="admin_chat_id", value="", description="ID чата администратора"),
                Setting(key="manager_chat_id", value="", description="ID чата менеджеров"),
                Setting(key="welcome_message", value="Добро пожаловать в Changify! Бот для P2P-обмена криптовалют и фиатных валют.", description="Приветственное сообщение")
            ]
            session.add_all(settings)
            session.commit()
            logger.info("Добавлены начальные настройки")
            
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Ошибка при заполнении начальных данных: {e}")
        raise

def create_admin_user(session, telegram_id, username=None, first_name=None, last_name=None):
    """Создает пользователя с правами администратора"""
    try:
        # Проверяем, существует ли пользователь
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if user:
            # Если пользователь существует, обновляем роль
            user.role = UserRole.ADMIN
            logger.info(f"Пользователь {telegram_id} обновлен до администратора")
        else:
            # Создаем нового пользователя с ролью администратора
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.ADMIN
            )
            session.add(user)
            logger.info(f"Создан новый пользователь-администратор {telegram_id}")
        
        session.commit()
        return user
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Ошибка при создании администратора: {e}")
        raise

def get_or_create_user(session, user_data):
    """
    Получает пользователя из базы или создает нового
    
    user_data должен содержать:
    - telegram_id: ID пользователя в Telegram
    - username: имя пользователя (опционально)
    - first_name: имя (опционально)
    - last_name: фамилия (опционально)
    - language_code: код языка (опционально)
    """
    try:
        user = session.query(User).filter_by(telegram_id=user_data['telegram_id']).first()
        
        if not user:
            # Создаем нового пользователя
            user = User(
                telegram_id=user_data['telegram_id'],
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                language_code=user_data.get('language_code', 'uk')
            )
            session.add(user)
            session.commit()
            logger.info(f"Создан новый пользователь {user_data['telegram_id']}")
        else:
            # Обновляем информацию о существующем пользователе
            user.username = user_data.get('username', user.username)
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.last_active = user_data.get('last_active', user.last_active)
            session.commit()
            
        return user
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Ошибка при получении/создании пользователя: {e}")
        raise