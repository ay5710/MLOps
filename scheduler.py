import schedule
import subprocess
import time

from src.utils.logger import setup_logging, get_backend_logger


setup_logging()
logger = get_backend_logger()
logger.info("Launching scheduler")


def run_main_py():
    try:
        subprocess.run(["python", "main.py"], check=True) # Raise an exception if the subprocess returns a nonzero exit code
        logger.info("Starting main.py")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing main.py: {e}")
    except FileNotFoundError:
        logger.error("Main.py not found")
 
# Schedule the job to run every hour
schedule.every().hour.do(run_main_py)

while True:
    schedule.run_pending()
    time.sleep(1)
