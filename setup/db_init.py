import numpy as np
import pandas as pd

from src.scrapping import IMDb
from src.utils.db import PostgreSQLDatabase
from src.utils.logger import setup_logging, get_backend_logger
from src.utils.s3 import s3


setup_logging()
logger = get_backend_logger()
logger.info("Initializing databases...")


# Drop existing tables for a clean start (in reverse order of dependency)
for table in ['reviews_sentiments', 'reviews_raw', 'movies']:
    with PostgreSQLDatabase() as db:
        if db.table_exists(table):
            db.drop_table(table)


# Create tables
with PostgreSQLDatabase() as db:
    db.create_table('movies', {
        'movie_id': 'VARCHAR(9) PRIMARY KEY',
        'title': 'VARCHAR(250)',
        'release_date': 'DATE',
        'nb_reviews': 'INTEGER',
        'scrapping_timestamp': 'TIMESTAMP'})

    db.create_table('reviews_raw', {
        'movie_id': 'VARCHAR(9) REFERENCES movies(movie_id) ON DELETE CASCADE',
        'review_id': 'VARCHAR(10)',
        'author': 'VARCHAR(150) PRIMARY KEY',
        'title': 'VARCHAR(500)',
        'text': 'TEXT',
        'rating': 'INTEGER',
        'date': 'DATE',
        'upvotes': 'INTEGER',
        'downvotes': 'INTEGER',
        'last_update': 'TIMESTAMP',
        'to_process': 'INTEGER'})

    db.create_table('reviews_sentiments', {
        'review_id': 'VARCHAR(10)',
        'author': 'VARCHAR(150) PRIMARY KEY REFERENCES reviews_raw(author) ON DELETE CASCADE',
        'story': 'INTEGER',
        'acting': 'INTEGER',
        'visuals': 'INTEGER',
        'sounds': 'INTEGER',
        'values': 'INTEGER',
        'overall': 'INTEGER'})


# Restore covers and data
s3 = s3()
s3.restore_covers()

for table in ['movies', 'reviews_raw', 'reviews_sentiments']:
    backup_df = s3.load_latest_backup(table)

    if backup_df is not None:
    # NaNs must be converted to None / NULL before being passed to postgreSQL
        if table == 'reviews_raw':
            # Replace NaN values with None in the rating column (not applicable to the df as whole because of str columns)
            backup_df['rating'] = backup_df['rating'].astype('float').replace({np.nan: None})
            # Verify no NaNs remain
            non_none_nulls = sum(1 for x in backup_df['rating'] if pd.isna(x) and x is not None)
            if non_none_nulls > 0:
                logger.error(f"{non_none_nulls} NaNs found in reviews_raw, backup not restored")
                continue

        if table == 'reviews_sentiments':
            # Apply replacement to all columns
            for col in backup_df.columns:
                backup_df[col] = backup_df[col].replace({np.nan: None})
            # Verify no NaNs remain
            non_none_nulls = sum(1 for row in backup_df.values.flatten() if pd.isna(row) and row is not None)
            if non_none_nulls > 0:
                logger.error(f"{non_none_nulls} NaNs found in reviews_sentiments, backup not restored")
                continue

        # Create tuples for database insertion, ensuring proper handling of None values
        backup_data = [
            tuple(None if pd.isna(value) else (str(value) if isinstance(value, str) else value)
                  for value in row)
            for row in backup_df.itertuples(index=False, name=None)
        ]

        with PostgreSQLDatabase() as db:
            db.insert_data(table, backup_data)

