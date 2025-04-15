import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_LEVELS, LOG_LEVEL, LOG_FILE, BASE_DIR

def setup_logger(name=None):
    """
    Настраивает и возвращает логгер с заданным именем
    
    Args:
        name (str): Имя логгера. Если None, возвращает корневой логгер
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.INFO))
    
    # Проверяем, есть ли уже обработчики
    if not logger.handlers:
        log_dir = os.path.join(BASE_DIR, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
        log_path = os.path.join(log_dir, LOG_FILE)
    
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=10*1024*1024, 
            backupCount=5
        )
        file_handler.setFormatter(formatter)
    
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
    
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger