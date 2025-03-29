import os
import pandas as pd
import psycopg

from dotenv import load_dotenv
from datetime import datetime
from psycopg import sql


class PostgreSQLDatabase:
    def __init__(self, admin=False):
        """
        Initialize database connection parameters.
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

    def connect(self):
        """
        Establish a connection to the PostgreSQL database.
        """
        try:
            self.connection = psycopg.connect(**self.connection_params)
            self.cursor = self.connection.cursor()
            print(f"Successfully connected to {self.connection_params['host']}")
        except (Exception, psycopg.Error) as error:
            print(f"Error while connecting to {self.connection_params['host']}: {error}")


    def table_exists(self, table_name):
        """
        Check if a table exists in the database.

        :param table_name: Name of the table to check
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
            print(f"Error checking if {table_name} exists: {error}")
            return False

            
    def create_table(self, table_name, columns):
        """
        Create a new table in the database.
        
        :param table_name: Name of the table to create
        :param columns: Dictionary of column names and their data types
        """
        try:
            create_table_query = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(
                    sql.SQL("{} {}").format(
                        sql.Identifier(col_name), 
                        sql.SQL(col_type)
                    ) for col_name, col_type in columns.items()
                )
            )
            
            self.cursor.execute(create_table_query)
            self.connection.commit()
            print(f"Table {table_name} created successfully")
        except (Exception, psycopg.Error) as error:
            print(f"Error creating table: {error}")

    
    def drop_table(self, table_name):
        """
        Drop an existing table from the database.
    
        :param table_name: Name of the table to drop
        """
        try:
            # Construct DROP TABLE statement
            drop_table_query = sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name)
            )
        
            self.cursor.execute(drop_table_query)
            self.connection.commit()
            print(f"Table {table_name} dropped successfully")
        except (Exception, psycopg.Error) as error:
            print(f"Error dropping table: {error}")

    
    def backup_table(self, table_name):
        """
        Backup a table to a Parquet file in the data/backups/ directory.
        
        :param table_name: Name of the table to backup
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
            
            # Get column names
            column_names = [desc[0] for desc in self.cursor.description]
            
            # Fetch all rows
            rows = self.cursor.fetchall()
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            # Save as Parquet
            df.to_parquet(backup_path, index=False)
            
            print(f"Table {table_name} backed up to {backup_path}")
            return None
        
        except (Exception, psycopg.Error) as error:
            print(f"Error backing up table {table_name}: {error}")
            return None

    
    def insert_data(self, table_name, data):
        """
        Insert data into a specified table.
        
        :param table_name: Name of the table
        :param data: List of tuples containing row data
        """
        try:
            # Prepare insert statement
            insert_query = sql.SQL("INSERT INTO {} VALUES ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(sql.Placeholder() * len(data[0]))
            )
            
            # Execute batch insert
            self.cursor.executemany(insert_query, data)
            self.connection.commit()
            print(f"Inserted {len(data)} rows into {table_name}")
        except (Exception, psycopg.Error) as error:
            print(f"Error inserting data: {error}")

        
    def remove_data(self, table_name, condition_column, condition_value):
        """
        Remove data from a specified table based on a condition.

        :param table_name: Name of the table
        :param condition_column: Column name for the condition
        :param condition_value: Value to match for deletion
        """
        try:
            # Prepare delete statement
            delete_query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
                sql.Identifier(table_name),
                sql.Identifier(condition_column)
            )
        
            # Execute delete query
            self.cursor.execute(delete_query, (condition_value,))
            self.connection.commit()
            print(f"Deleted rows from {table_name} where {condition_column} = {condition_value}")
    
        except (Exception, psycopg.Error) as error:
            print(f"Error deleting data: {error}")

    
    def query_data(self, table_name, columns='*', condition=None):
        """
        Query data from a specified table.
        
        :param table_name: Name of the table
        :param columns: Columns to select (default: all)
        :param condition: Optional WHERE clause
        :return: List of query results
        """
        try:
            # Prepare select statement
            if columns == '*':
                select_query = sql.SQL("SELECT * FROM {}").format(
                    sql.Identifier(table_name)
                )
                if condition:
                    select_query = sql.SQL("SELECT * FROM {} WHERE {}").format(
                        sql.Identifier(table_name),
                        sql.SQL(condition)
                    )
            else:
                select_query = sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(', ').join(sql.Identifier(col) for col in columns),
                    sql.Identifier(table_name)
                )
                if condition:
                    select_query = sql.SQL("SELECT {} FROM {} WHERE {}").format(
                        sql.SQL(', ').join(sql.Identifier(col) for col in columns),
                        sql.Identifier(table_name),
                        sql.SQL(condition)
                    )
            
            self.cursor.execute(select_query)
            results = self.cursor.fetchall()
            return results
        except (Exception, psycopg.Error) as error:
            print(f"Error querying data: {error}")
            return []

    
    def close_connection(self):
        """
        Close database connection and cursor.
        """
        if self.connection:
            self.cursor.close()
            self.connection.close()
            print("Database connection closed")