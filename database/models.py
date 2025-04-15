# database/models.py
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"

class OrderStatus(enum.Enum):
    CREATED = "created"                # Создана
    AWAITING_PAYMENT = "awaiting_payment"  # Ожидает оплаты
    PAYMENT_CONFIRMED = "payment_confirmed"  # Пользователь подтвердил оплату
    PROCESSING = "processing"          # Проверяется менеджером
    COMPLETED = "completed"            # Завершена
    CANCELLED = "cancelled"            # Отменена

class CurrencyType(enum.Enum):
    CRYPTO = "crypto"
    FIAT = "fiat"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(50), nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    language_code = Column(String(10), default='uk')
    
    # Связанные объекты
    orders = relationship("Order", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"

class Currency(Base):
    __tablename__ = 'currencies'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False)  # USDT, USD, UAH
    name = Column(String(50), nullable=False)  # Tether, US Dollar, Ukrainian Hryvnia
    type = Column(Enum(CurrencyType), nullable=False)  # CRYPTO или FIAT
    enabled = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Currency(id={self.id}, code={self.code}, type={self.type})>"

class Bank(Base):
    __tablename__ = 'banks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)  # ПриватБанк, Монобанк, ПУМБ
    currency_id = Column(Integer, ForeignKey('currencies.id'))
    enabled = Column(Boolean, default=True)
    
    currency = relationship("Currency")
    
    def __repr__(self):
        return f"<Bank(id={self.id}, name={self.name})>"

class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    
    id = Column(Integer, primary_key=True)
    from_currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    to_currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    rate = Column(Float, nullable=False)  # Курс обмена
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    from_currency = relationship("Currency", foreign_keys=[from_currency_id])
    to_currency = relationship("Currency", foreign_keys=[to_currency_id])
    
    def __repr__(self):
        return f"<ExchangeRate(from={self.from_currency_id}, to={self.to_currency_id}, rate={self.rate})>"

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    from_currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    to_currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)
    amount_from = Column(Float, nullable=False)  # Сумма отправления
    amount_to = Column(Float, nullable=False)    # Сумма получения
    rate = Column(Float, nullable=False)         # Зафиксированный курс
    status = Column(Enum(OrderStatus), default=OrderStatus.CREATED)
    bank_id = Column(Integer, ForeignKey('banks.id'), nullable=True)  # Банк (для UAH)
    payment_details = Column(Text)  # Реквизиты для оплаты (wallet address, bank account, etc.)
    user_comment = Column(Text)  # Комментарий пользователя
    manager_comment = Column(Text)  # Комментарий менеджера
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    manager_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Менеджер, обрабатывающий заявку
    
    user = relationship("User", back_populates="orders", foreign_keys=[user_id])
    manager = relationship("User", foreign_keys=[manager_id])
    from_currency = relationship("Currency", foreign_keys=[from_currency_id])
    to_currency = relationship("Currency", foreign_keys=[to_currency_id])
    bank = relationship("Bank")
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, status={self.status})>"

class Setting(Base):
    __tablename__ = 'settings'
    
    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Setting(key={self.key}, value={self.value})>"

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(50), nullable=False)  # Тип действия (create_order, update_rate, etc.)
    entity_type = Column(String(50))  # Тип сущности (order, rate, user, etc.)
    entity_id = Column(Integer)  # ID сущности
    details = Column(Text)  # Детали действия
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action})>"