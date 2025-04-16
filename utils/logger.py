# utils/logger.py

import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_LEVELS, LOG_LEVEL, LOG_FILE, BASE_DIR

_loggers = {}

def setup_logger(name=None):
    """
    Настраивает и возвращает логгер с заданным именем
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        log_dir = os.path.join(BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, LOG_FILE)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    _loggers[name] = logger
    return logger
