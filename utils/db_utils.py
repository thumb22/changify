from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.exc import SQLAlchemyError
import logging
from database.models import Currency, Bank, ExchangeRate, Setting

logger = logging.getLogger(__name__)

async def get_all_currencies(session, enabled_only=True):
    """
    Получить все валюты из базы данных
    
    Args:
        engine: SQLAlchemy engine
        enabled_only (bool): Если True, возвращать только активные валюты
        
    Returns:
        list: Список объектов Currency
    """
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

async def get_exchange_rate(session, from_currency_code, to_currency_code):
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

def set_exchange_rate(session, from_currency_code, to_currency_code, rate):
    try:
        from_currency = session.query(Currency).filter_by(code=from_currency_code).first()
        to_currency = session.query(Currency).filter_by(code=to_currency_code).first()

        if not from_currency or not to_currency:
            logger.error(f"Одна из валют не найдена: {from_currency_code} → {to_currency_code}")
            return False

        existing_rate = session.query(ExchangeRate).filter_by(
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id
        ).first()

        if existing_rate:
            existing_rate.rate = rate
            existing_rate.updated_at =  datetime.now(ZoneInfo("Europe/Kyiv"))
            logger.info(f"Обновлен курс {from_currency_code} → {to_currency_code} до {rate}")
        else:
            new_rate = ExchangeRate(
                from_currency_id=from_currency.id,
                to_currency_id=to_currency.id,
                rate=rate
            )
            session.add(new_rate)
            logger.info(f"Добавлен курс {from_currency_code} → {to_currency_code}: {rate}")

        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Ошибка при установке курса обмена: {e}")
        return False

async def get_banks_for_currency(session, currency_code):
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

async def get_setting(session, key, default=None):
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