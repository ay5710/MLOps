import sys

from src.utils.db import PostgreSQLDatabase
from src.utils.logger import get_backend_logger

logger = get_backend_logger()

def add_movie(movie_id):
    """Adds a movie ID to the database"""
    db = PostgreSQLDatabase()
    db.connect()
    db.insert_data("movies", data=[(movie_id, None, None, None, None)])
    db.close_connection()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.warning("movie_id must be passed in this way: python your_script_name.py <movie_id>")
        sys.exit(1)
    try:
        movie_id = sys.argv[1]
        add_movie(movie_id)
    except ValueError:
        logger.error("movie_id must be a string")
        sys.exit(1)
