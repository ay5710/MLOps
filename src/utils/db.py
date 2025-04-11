import os
import pandas as pd
import psycopg

from dotenv import load_dotenv
from datetime import datetime
from psycopg import sql
from src.utils.logger import get_backend_logger

logger = get_backend_logger()


class PostgreSQLDatabase:
    def __init__(self, admin=False):
        """
        Initialize database connection parameters
        """
        load_dotenv()
        self.connection_params = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_ADMIN_USER') if admin else os.getenv('DB_USER'),
            'password': os.getenv('DB_ADMIN_PASSWORD') if admin else os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': 5432
        }
        self.connection = None
        self.cursor = None


    def __enter__(self):
        """
        Establish a connection to the PostgreSQL database
        """
        try:
            self.connection = psycopg.connect(**self.connection_params)
            self.cursor = self.connection.cursor()
            logger.debug(f"Successfully connected to {self.connection_params['host']}")
            return self
        except (Exception, psycopg.Error) as error:
            logger.error(f"Failed connecting to {self.connection_params['host']}: {error}")
            raise


    def __exit__(self, exc_type, exc_value, traceback):
        """
        Close database connection and cursor
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.debug("Database connection closed")


######################################
#               Tables               #
######################################


    def table_exists(self, table_name):
        """
        Check if a table exists in the database
        """
        try:
            check_query = sql.SQL("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """)
            self.cursor.execute(check_query, (table_name,))
            return self.cursor.fetchone()[0]
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"Failed checking if {table_name} exists: {error}")
            return False


    def create_table(self, table_name, columns):
        """
        Create a new table in the database

        :table_name: Name of the table to create
        :columns: Dictionary of column names and their data types
        """
        try:
            create_table_query = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(
                    sql.SQL("{} {}").format(
                        sql.Identifier(col_name),
                        sql.SQL(col_type)
                    ) for col_name, col_type in columns.items()))
            self.cursor.execute(create_table_query)
            self.connection.commit()
            logger.info(f"Table {table_name} created successfully")
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"Failed creating table: {error}")


    def drop_table(self, table_name):
        """
        Drop an existing table from the database
        """
        try:
            drop_table_query = sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name))
            self.cursor.execute(drop_table_query)
            self.connection.commit()
            logger.info(f"Table {table_name} dropped successfully")
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"Failed dropping table: {error}")


    def backup_table(self, table_name):
        """
        Backup a table to a Parquet file in the data/backups/ directory
        """
        try:
            # Ensure backup directory exists
            backup_dir = os.path.join('data', 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{table_name}_{timestamp}.parquet"
            backup_path = os.path.join(backup_dir, backup_filename)
            # Fetch all data from the table
            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
            self.cursor.execute(query)
            column_names = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            df = pd.DataFrame(rows, columns=column_names)
            # Save as Parquet
            df.to_parquet(backup_path, index=False)
            logger.info(f"Table {table_name} backed up to {backup_path}")
            return None
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"Failed backing up table {table_name}: {error}")
            return None


######################################
#       Generic data functions       #
######################################


    def insert_data(self, table_name, data, movie_id=None):
        """
        Insert data into a specified table

        :param table_name: Name of the table
        :param data: List of tuples containing row data
        """
        try:
            insert_query = sql.SQL("INSERT INTO {} VALUES ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(sql.Placeholder() * len(data[0])))
            self.cursor.executemany(insert_query, data)
            self.connection.commit()
            prompt = "1 row" if len(data) == 1 else f"{len(data)} rows"
            if movie_id:
                logger.debug(f"{movie_id} - Inserted {prompt} into {table_name}")
            else:
                logger.debug(f"Inserted {prompt} into {table_name}")
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            if movie_id:
                logger.error(f"{movie_id} - Failed inserting data: {error} ({str(error)})")
            else:
                logger.error(f"Failed inserting data: {error} ({str(error)})")


    def remove_data(self, table_name, condition_column, condition_value, movie_id=None):
        """
        Remove data from a specified table based on a condition

        :param table_name: Name of the table
        :param condition_column: Column name for the condition
        :param condition_value: Value to match for deletion
        """
        try:
            delete_query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
                sql.Identifier(table_name),
                sql.Identifier(condition_column))
            self.cursor.execute(delete_query, (condition_value,))
            row_count = self.cursor.rowcount
            self.connection.commit()
            prompt = "1 row" if row_count == 1 else f"{row_count} rows"
            if movie_id:
                logger.debug(f"{movie_id} - Deleted {prompt} from {table_name} where {condition_column} = {condition_value}")
            else:
                logger.debug(f"Deleted {prompt} from {table_name} where {condition_column} = {condition_value}")
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            if movie_id:
                logger.error(f"{movie_id} - Failed deleting data: {error}")
            else:
                logger.error(f"Failed deleting data: {error}")


    def query_data(self, table_name, columns='*', condition=None, movie_id=None):
        """
        Query data from a specified table

        :param table_name: Name of the table
        :param columns: Columns to select (default: all)
        :param condition: Optional WHERE clause
        :return: List of query results
        """
        try:
            if columns == '*':
                select_query = sql.SQL("SELECT * FROM {}").format(
                    sql.Identifier(table_name))
            else:
                select_query = sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(', ').join(sql.Identifier(col) for col in columns),
                    sql.Identifier(table_name))

            # Append condition if provided
            if condition:
                select_query = sql.SQL("{} WHERE {}").format(select_query, sql.SQL(condition))

            query_string = select_query.as_string(self.connection)
            logger.debug(f"Executing SQL: {query_string}")
        
            self.cursor.execute(select_query)
            results = self.cursor.fetchall()
            return results
            
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            if movie_id:
                logger.error(f"{movie_id} - Failed querying data: {error}")
            else:
                logger.error(f"Failed querying data: {error}")
            return []


######################################
#       Specific data functions       #
######################################


    def upsert_movie_data(self, data, movie_id):
        try:
            query = sql.SQL("""
                    INSERT INTO {} (movie_id, title, release_date, nb_reviews, scrapping_timestamp)
                    VALUES ({})
                    ON CONFLICT (movie_id)
                    DO UPDATE SET
                        nb_reviews = EXCLUDED.nb_reviews,
                        scrapping_timestamp = EXCLUDED.scrapping_timestamp
                    WHERE {}.nb_reviews <> EXCLUDED.nb_reviews
                """).format(
                    sql.Identifier('movies'),
                    sql.SQL(', ').join(sql.Placeholder() * len(data[0])),
                    sql.Identifier('movies'))
            self.cursor.executemany(query, data)
            self.connection.commit()
            logger.info(f"{movie_id} - Upserted metadata successfully")
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"{movie_id} - Failed upserting metadata: {error}")


    def upsert_review_data(self, data, movie_id):
        try:
            query = """
            INSERT INTO reviews_raw (movie_id, review_id, author, title, text, rating, date, upvotes, downvotes, last_update, to_process)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (author) DO UPDATE
            SET
                title = EXCLUDED.title,
                text = EXCLUDED.text,
                upvotes = EXCLUDED.upvotes,
                downvotes = EXCLUDED.downvotes,
                last_update = EXCLUDED.last_update,
                to_process = CASE
                    WHEN reviews_raw.title IS DISTINCT FROM EXCLUDED.title OR reviews_raw.text IS DISTINCT FROM EXCLUDED.text
                    THEN 1
                    ELSE reviews_raw.to_process
            END;
            """
            self.cursor.executemany(query, data)
            self.connection.commit()
            logger.info(f"{movie_id} - Upserted reviews successfully")
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"{movie_id} - Failed upserting reviews: {error}")


    def update_sentiment_data(self, data, movie_id):
        try:
            self.cursor.execute(sql.SQL("SELECT column_name FROM information_schema.columns WHERE table_name = 'reviews_sentiments' ORDER BY ordinal_position;"))
            columns = [row[0] for row in self.cursor.fetchall()]
            update_assignments = sql.SQL(', ').join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
                for col in columns if col != 'author')  # Exclude primary key from updates

            insert_query = sql.SQL("""
                INSERT INTO {} ({}) VALUES ({})
                ON CONFLICT (author) DO UPDATE SET {}
            """).format(
                sql.Identifier('reviews_sentiments'),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(columns)),
                update_assignments)
            self.cursor.executemany(insert_query, data)
            self.connection.commit()
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"{movie_id} - Failed updating sentiment data: {error}")


    def reset_indicator(self, author, movie_id):
        try:
            query = "UPDATE reviews_raw SET to_process = 0 WHERE author = %s"
            self.cursor.execute(query, (author,))
            self.connection.commit()
            logger.debug(f"{movie_id} - Reseted indicator for review by {author}")
        except (Exception, psycopg.Error) as error:
            self.connection.rollback()
            logger.error(f"{movie_id} - Failed resetting process indicator for review by {author}: {error}")
