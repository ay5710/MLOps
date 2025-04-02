import numpy as np
import os
import pandas as pd
import re
import s3fs

from datetime import datetime
from src.utils.db import PostgreSQLDatabase


# Connect to database
db = PostgreSQLDatabase()
db.connect()


# Connect to S3
S3_ENDPOINT_URL = 'https://' + os.environ['AWS_S3_ENDPOINT']
fs = s3fs.S3FileSystem(client_kwargs={'endpoint_url': S3_ENDPOINT_URL})
bucket_name = 'maeldieudonne'
destination = bucket_name + '/diffusion/'


# Drop existing tables for a clean start (in reverse order of dependency)
for table in ['reviews_sentiments', 'reviews_raw', 'movies']:
    if db.table_exists(table):
        db.drop_table(table)


# Create tables
db.create_table(
    'movies', {
        'movie_id': 'VARCHAR(10) PRIMARY KEY',
        'title': 'VARCHAR(250)',
        'release_date': 'DATE',
        'nb_reviews': 'INTEGER',
        'scrapping_timestamp': 'TIMESTAMP'})
    
db.create_table(
    'reviews_raw', {
        'movie_id': 'VARCHAR(10) REFERENCES movies(movie_id) ON DELETE CASCADE',
        'review_id': 'VARCHAR(10) PRIMARY KEY',
        'author': 'VARCHAR(150)',
        'title': 'VARCHAR(500)',
        'text': 'TEXT',
        'rating': 'INTEGER',
        'date': 'DATE',
        'upvotes': 'INTEGER',
        'downvotes': 'INTEGER',
        'last_update': 'TIMESTAMP',
        'to_process': 'INTEGER'})

db.create_table(
    'reviews_sentiments', {
        'review_id': 'VARCHAR(10) PRIMARY KEY REFERENCES reviews_raw(review_id) ON DELETE CASCADE',
        'story': 'INTEGER',
        'acting': 'INTEGER',
        'visuals': 'INTEGER',
        'sounds': 'INTEGER',
        'values': 'INTEGER',
        'overall': 'INTEGER'})


# Get latest backup or sample data for a given table
def extract_timestamp(file_name):
    match = re.search(r'(\d{8}_\d{6})', file_name)
    if match:
        return datetime.strptime(match.group(1), '%Y%m%d_%H%M%S')
    return None
    
def load_latest_backup(table_name):
    # Look for a backup in S3
    all_files = [f['name'] for f in fs.listdir(destination)]
    backup_files = [f for f in all_files if f.startswith(f"{destination}{table_name}")]

    if not backup_files:
        # Look for sample data locally
        try:
            backup = pd.read_csv(f"data/sample/{table_name}.csv")
            print(f"[INFO] Loading sample data for {table_name}")
            return backup
        except:
            print(f"[WARNING] No distant or local backup found for {table_name}")

    else:
        file_path = max(backup_files, key=extract_timestamp)
        timestamp = extract_timestamp(file_path).strftime('%Y-%m-%d %H:%M:%S')
        with fs.open(f's3://{file_path}', 'rb') as f:
            backup = pd.read_parquet(f)
        print(f"[INFO] Loading distant backup for {table_name}: {timestamp}")
        return backup


# NaNs must be converted to None / NULL before being passed to postgreSQL
for table in ['movies', 'reviews_raw', 'reviews_sentiments']:
    backup_df = load_latest_backup(table)
    
    if backup_df is not None:
        if table == 'reviews_raw':
            # Replace NaN values with None in the rating column (not applicable to the df as whole because of str columns)
            backup_df['rating'] = backup_df['rating'].astype('float').replace({np.nan: None})
            # Verify no NaNs remain
            non_none_nulls = sum(1 for x in backup_df['rating'] if pd.isna(x) and x is not None)
            if non_none_nulls > 0:
                print(f"[ERROR] {non_none_nulls} NaNs found in reviews_raw, backup not restored")
                continue
        
        if table == 'reviews_sentiments':
            # Apply replacement to all columns
            for col in backup_df.columns:
                backup_df[col] = backup_df[col].replace({np.nan: None})
            # Verify no NaNs remain
            non_none_nulls = sum(1 for row in backup_df.values.flatten() if pd.isna(row) and row is not None)
            if non_none_nulls > 0:
                print(f"[ERROR] {non_none_nulls} NaNs found in reviews_sentiments, backup not restored")
                continue
        
        # Create tuples for database insertion, ensuring proper handling of None values
        backup_data = [
            tuple(None if pd.isna(value) else (str(value) if isinstance(value, str) else value) 
                 for value in row)
            for row in backup_df.itertuples(index=False, name=None)
        ]
        
        db.insert_data(table, backup_data)


db.close_connection()