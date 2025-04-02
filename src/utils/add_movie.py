import sys

from src.utils.db import PostgreSQLDatabase


def add_movie(movie_id):
    """Adds a movie ID to the database"""
    db = PostgreSQLDatabase()
    db.connect()
    db.insert_data("movies", data=[(movie_id, None, None, None, None)])
    db.close_connection()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Movie_id must be passed in this way: python your_script_name.py <movie_id>")
        sys.exit(1)
    try:
        movie_id = sys.argv[1]
        add_movie(movie_id)
    except ValueError:
        print("Error: Movie ID must be an integer.")
        sys.exit(1)
