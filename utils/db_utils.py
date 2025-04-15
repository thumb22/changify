from sqlalchemy.exc import SQLAlchemyError
import logging
from database.db_operations import get_session
from database.models import Currency, Bank, ExchangeRate, Setting

logger = logging.getLogger(__name__)

async def get_all_currencies(engine, enabled_only=True):
    """
    Получить все валюты из базы данных
    
    Args:
        engine: SQLAlchemy engine
        enabled_only (bool): Если True, возвращать только активные валюты
        
    Returns:
        list: Список объектов Currency
    """
    session = get_session(engine)
    try:
        query = session.query(Currency)
        if enabled_only:
            query = query.filter_by(enabled=True)
        currencies = query.all()
        return currencies
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении валют: {e}")
        return []
    finally:
        session.close()

async def get_exchange_rate(engine, from_currency_code, to_currency_code):
    """
    Получить курс обмена для пары валют
    
    Args:
        engine: SQLAlchemy engine
        from_currency_code (str): Код валюты, которую меняем
        to_currency_code (str): Код валюты, на которую меняем
        
    Returns:
        float: Курс обмена или None в случае ошибки
    """
    session = get_session(engine)
    try:
        from_currency = session.query(Currency).filter_by(code=from_currency_code).first()
        to_currency = session.query(Currency).filter_by(code=to_currency_code).first()
        
        if not from_currency or not to_currency:
            return None
            
        exchange_rate = session.query(ExchangeRate).filter_by(
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id
        ).first()
        
        if exchange_rate:
            return exchange_rate.rate
        return None
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении курса обмена: {e}")
        return None
    finally:
        session.close()

async def get_banks_for_currency(engine, currency_code):
    """
    Получить список банков для указанной валюты
    
    Args:
        engine: SQLAlchemy engine
        currency_code (str): Код валюты
        
    Returns:
        list: Список объектов Bank
    """
    session = get_session(engine)
    try:
        currency = session.query(Currency).filter_by(code=currency_code).first()
        
        if not currency:
            return []
            
        banks = session.query(Bank).filter_by(
            currency_id=currency.id,
            enabled=True
        ).all()
        
        return banks
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении банков для валюты: {e}")
        return []
    finally:
        session.close()

async def get_setting(engine, key, default=None):
    """
    Получить значение настройки по ключу
    
    Args:
        engine: SQLAlchemy engine
        key (str): Ключ настройки
        default: Значение по умолчанию, если настройка не найдена
        
    Returns:
        str: Значение настройки или default в случае ошибки
    """
    session = get_session(engine)
    try:
        setting = session.query(Setting).filter_by(key=key).first()
        
        if setting:
            return setting.value
        return default
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении настройки {key}: {e}")
        return default
    finally:
        session.close()