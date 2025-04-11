import argparse
import sys

from src.utils.db import PostgreSQLDatabase
from src.utils.logger import setup_logging, get_backend_logger

setup_logging()
logger = get_backend_logger()


def add_movie(movie_id):
    """Adds a movie ID to the database"""
    with PostgreSQLDatabase() as db:
        try:
            result = db.query_data("movies", condition=f"movie_id = '{movie_id}'")
            if result:
                logger.warning(f"Movie #{movie_id} already present in the database")
            else:
                db.insert_data("movies", data=[(movie_id, None)])
                logger.info(f"Added movie #{movie_id} to the database")
        except Exception as e:
            logger.error(f"Failed to add movie #{movie_id} to the database: {e}")



def remove_movie(movie_id):
    """Removes a movie and the corresponding reviews"""
    with PostgreSQLDatabase() as db:
        try:
            result = db.query_data("movies", condition=f"movie_id = '{movie_id}'")
            if result:
                db.remove_data("movies", "movie_id", movie_id)
                logger.info(f"Removed movie #{movie_id} from the database")
            else:
                logger.warning(f"Movie #{movie_id} not found in the database")
        except Exception as e:
            logger.error(f"Failed to remove movie #{movie_id} from the database: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add or remove movies by ID.")
    parser.add_argument("--add", nargs="*", help="One or more Movie IDs to add")
    parser.add_argument("--remove", nargs="*", help="One or more Movie IDs to remove")

    args = parser.parse_args()

    if not args.add and not args.remove:
        parser.error("At least one of --add or --remove argument must be provided.")

    try:
        if args.add:
            for movie_id in args.add:
                add_movie(movie_id)

        if args.remove:
            for movie_id in args.remove:
                remove_movie(movie_id)

    except ValueError as e:
        logger.error(f"Command {args} failed: {e}")
        sys.exit(1)
