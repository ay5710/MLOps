import multiprocessing
import subprocess
import time
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.utils.db import PostgreSQLDatabase
from src.utils.logger import setup_logging, get_backend_logger

setup_logging()
logger = get_backend_logger()
logger.info("Launching scheduler for movie processing and backups")

max_concurrent_scripts = 5
processing_lock = threading.Lock()
active_processes = set()


def run_movie_script(movie_id):
    """Runs the main script for a single movie."""
    with processing_lock:
        if movie_id in active_processes:
            logger.warning(f"Script already running for movie #{movie_id}. Skipping...")
            return
        active_processes.add(movie_id)

    try:
        command = f"python main.py --movie_id '{movie_id}'"
        logger.debug(f"Launching main script for movie #{movie_id}...")
        subprocess.run(command, shell=True, check=True)
        logger.debug(f"Main script finished for movie #{movie_id}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed launching main script for movie {movie_id}: {e}")
    finally:
        with processing_lock:
            active_processes.remove(movie_id)


def process_movies(movies_id):
    """Manages concurrent execution of movie scripts."""
    semaphore = multiprocessing.Semaphore(max_concurrent_scripts)

    def worker(movie_id):
        with semaphore:
            run_movie_script(movie_id)

    logger.info(f"Processing {len(movies_id)} movies with {max_concurrent_scripts} concurrent workers.")
    with multiprocessing.Pool(processes=max_concurrent_scripts) as pool:
        pool.map(worker, list(movies_id))
    logger.info("All movie processing completed.")


def backup_function():
    """Runs the backup script."""
    try:
        subprocess.run("python src/backup.py", shell=True, check=True)
        logger.info("Backup completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed running backup: {e}")


def schedule_tasks():
    """Schedules the movie processing and backup."""
    scheduler = BackgroundScheduler()

    def scheduled_movie_processing():
        with PostgreSQLDatabase() as db:
            movies_id = set(movie[0] for movie in db.query_data('movies'))
            if movies_id:
                process_movies(movies_id)
            else:
                logger.warning("No movies found in the database to process.")

    # Schedule movie processing to run at the top of every hour (0th minute)
    scheduler.add_job(scheduled_movie_processing, CronTrigger(minute=0))

    # Schedule backup to run every hour at the 50th minute
    scheduler.add_job(backup_function, CronTrigger(minute=50))

    scheduler.start()

    try:
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == '__main__':
    schedule_tasks()
