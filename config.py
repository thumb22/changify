# config.py
import os
from dotenv import load_dotenv
import logging
from pathlib import Path
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []
MANAGER_IDS = list(map(int, os.getenv('MANAGER_IDS', '').split(','))) if os.getenv('MANAGER_IDS') else []

DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite')
DB_NAME = os.getenv('DB_NAME', 'changify.db')
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', '')
DB_PORT = os.getenv('DB_PORT', '')

if DB_ENGINE == 'sqlite':
    DATABASE_URL = f"sqlite:///{BASE_DIR / DB_NAME}"
elif DB_ENGINE == 'postgresql':
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"sqlite:///{BASE_DIR / DB_NAME}"

EXCHANGE_API_KEY = os.getenv('EXCHANGE_API_KEY', '')
EXCHANGE_API_URL = os.getenv('EXCHANGE_API_URL', '')

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

CACHE_TTL = int(os.getenv('CACHE_TTL', 300))

DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'uk')
AVAILABLE_LANGUAGES = ['uk', 'en', 'ru']

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")