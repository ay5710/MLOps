import logging
import os


LOG_DIR = "logs"
BACKEND_LOG = os.path.join(LOG_DIR, "backend.log")
FRONTEND_LOG = os.path.join(LOG_DIR, "frontend.log")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    # Backend Logger
    backend_logger = logging.getLogger('backend')
    backend_logger.setLevel(logging.INFO)
    backend_file_handler = logging.FileHandler(BACKEND_LOG, mode='a')
    backend_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    backend_logger.addHandler(backend_file_handler)
    backend_logger.addHandler(console_handler)

    # Frontend Logger
    frontend_logger = logging.getLogger('frontend')
    frontend_logger.setLevel(logging.INFO)
    frontend_file_handler = logging.FileHandler(FRONTEND_LOG, mode='a')
    frontend_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    frontend_logger.addHandler(frontend_file_handler)
    frontend_logger.addHandler(console_handler)

def get_backend_logger():
    return logging.getLogger('backend')

def get_frontend_logger():
    return logging.getLogger('frontend')
