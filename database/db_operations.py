from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging

from utils.db_utils import set_exchange_rate

from .models import Base, Currency, CurrencyType, Bank, User, UserRole, Setting

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_engine(db_url="sqlite:///changify.db"):
    return create_engine(db_url, echo=False)

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

def init_db(engine):
    Base.metadata.create_all(engine)
    logger.info("База данных инициализирована")


def setup_initial_data(session):
    try:
        if session.query(Currency).count() == 0:
            currencies = [
                Currency(code="USDT", name="Tether", type=CurrencyType.CRYPTO),
                # Currency(code="USD", name="US Dollar", type=CurrencyType.FIAT),
                Currency(code="UAH", name="Ukrainian Hryvnia", type=CurrencyType.FIAT)
            ]
            session.add_all(currencies)
            session.commit()
            logger.info("Добавлены начальные валюты")
        
        uah = session.query(Currency).filter_by(code="UAH").first()
        
        usdt_to_uah_rate = 41.29 + (0.01 * 41.29)
        set_exchange_rate(session, "USDT", "UAH", usdt_to_uah_rate)
    
        uah_to_usdt_rate = 1 / usdt_to_uah_rate
        set_exchange_rate(session, "UAH", "USDT", uah_to_usdt_rate)
        
        if uah and session.query(Bank).count() == 0:
            banks = [
                Bank(name="ПриватБанк", currency_id=uah.id),
                Bank(name="Монобанк", currency_id=uah.id),
                Bank(name="ПУМБ", currency_id=uah.id)
            ]
            session.add_all(banks)
            session.commit()
            logger.info("Добавлены начальные банки")
        
        if session.query(Setting).count() == 0:
            settings = [
                Setting(key="bot_name", value="Changify", description="Название бота"),
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
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if user:
            user.role = UserRole.ADMIN
            logger.info(f"Пользователь {telegram_id} обновлен до администратора")
        else:
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
    try:
        user = session.query(User).filter_by(telegram_id=user_data['telegram_id']).first()
        
        if not user:
            user = User(
                telegram_id=user_data['telegram_id'],
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name')
            )
            session.add(user)
            session.commit()
            logger.info(f"Created new user {user_data['telegram_id']}")
        else:
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
    