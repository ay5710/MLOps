from src.utils.s3 import s3
from src.utils.logger import setup_logging, get_backend_logger
from src.utils.db import PostgreSQLDatabase

setup_logging()
logger = get_backend_logger()
logger.info("Backing up...")

s3 = s3()

# Save the tables to parquet
for table in ['movies', 'reviews_raw', 'reviews_sentiments']:
    with PostgreSQLDatabase() as db:
        db.backup_table(table)

# Upload the files to S3
for table in ['movies', 'reviews_raw', 'reviews_sentiments']:
    file_path = s3.get_latest_local_backup(table)
    if file_path is not None:
        s3.upload_backup(file_path)

# Remove old backups
s3.clean_backup_directory()
