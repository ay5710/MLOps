import colorlog
import logging
import os

from logging.handlers import RotatingFileHandler


LOG_DIR = "logs"
BACKEND_LOG = os.path.join(LOG_DIR, "backend.log")
FRONTEND_LOG = os.path.join(LOG_DIR, "frontend.log")
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logging():
    console_handler = logging.StreamHandler()
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    console_handler.setFormatter(color_formatter)

    # Backend Logger
    backend_logger = logging.getLogger('backend')
    backend_logger.setLevel(logging.DEBUG)
    backend_file_handler = RotatingFileHandler(
        BACKEND_LOG,
        mode='a',
        maxBytes=10*512*512,
        backupCount=5,
        encoding='utf-8')
    backend_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    backend_logger.addHandler(backend_file_handler)
    backend_logger.addHandler(console_handler)

    # Frontend Logger
    frontend_logger = logging.getLogger('frontend')
    frontend_logger.setLevel(logging.INFO)
    frontend_file_handler = RotatingFileHandler(
        FRONTEND_LOG,
        mode='a',
        maxBytes=10*512*512,
        backupCount=5,
        encoding='utf-8')
    frontend_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    frontend_logger.addHandler(frontend_file_handler)
    frontend_logger.addHandler(console_handler)


def get_backend_logger():
    return logging.getLogger('backend')


def get_frontend_logger():
    return logging.getLogger('frontend')
