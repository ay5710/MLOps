import concurrent.futures
import schedule
import subprocess
import time

from src.utils.logger import setup_logging, get_backend_logger


setup_logging()
logger = get_backend_logger()
logger.info("Launching scheduler to run every exact hour")

db = PostgreSQLDatabase()


def run_main_for_movie(movie_id):
    try:
        subprocess.run(["python", "main.py", "--movie_id", str(movie_id)], check=True)
        logger.info(f"Finished main.py for movie_id: {movie_id}")
    except subprocess.CalledProcessError as e:
        logger.error(f"main.py failed for movie_id {movie_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error for movie_id {movie_id}: {e}")


def run_main_for_all_movies():
    logger.info("Fetching movie_ids from database")
    with PostgreSQLDatabase() as db:
        movie_ids = set(movie[0] for movie in db.query_data('movies'))

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(run_main_for_movie, movie_id): movie_id for movie_id in movie_ids}

        for future in concurrent.futures.as_completed(futures):
            movie_id = futures[future]
            try:
                future.result()
            except Exception as exc:
                logger.error(f"main.py crashed for movie_id {movie_id}: {exc}")


# Schedule the job to run at the start of every hour
schedule.every().hour.at(":00").do(run_main_for_all_movies)

while True:
    schedule.run_pending()
    time.sleep(1)
