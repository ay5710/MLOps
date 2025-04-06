from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
import time

from src.utils.logger import setup_logging, get_backend_logger


setup_logging()
logger = get_backend_logger()
logger.info("Launching scheduler")


def run_main_py():
    try:
        logger.info(f"Starting main.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        subprocess.run(["python", "main.py"], check=True)
        logger.info(f"Main.py executed successfully at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Main.py raised error: {e}")
    except FileNotFoundError:
        logger.error("Main.py not found")

# Create a scheduler that won't run overlapping jobs
scheduler = BlockingScheduler()
scheduler.add_job(run_main_py, 'interval', hours=1, max_instances=1)

try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    pass

