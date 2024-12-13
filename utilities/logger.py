import os
import logging

from logging.handlers import TimedRotatingFileHandler


loggers = {}
LOG_PATH = os.environ.get("LOG_PATH", 'logs')

WHEN = "W0"
BACKUP_COUNT = 4


def get_logger(logger_name, log_level):
    global loggers
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH, exist_ok=True)
    
    log_file_name = logger_name + '.log'
    log_file_path = os.path.join(LOG_PATH, log_file_name)

    if loggers.get(logger_name):
        return loggers.get(logger_name)
    else:
        # Create a custom logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        # Create handlers
        c_handler = logging.StreamHandler()
        # The TimedRotatingFileHandler will rollover according to the when param
        f_handler = TimedRotatingFileHandler(log_file_path, when=WHEN, backupCount=BACKUP_COUNT)
        c_handler.setLevel(logging.DEBUG)

        # Create formatters and add it to handlers
        c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)
        loggers[logger_name] = logger
    return logger

