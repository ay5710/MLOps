import os
import pandas as pd
import re
import s3fs

from datetime import datetime
from dotenv import load_dotenv
from src.utils.logger import get_backend_logger

logger = get_backend_logger()


class s3:
    def __init__(self):
        """
        Initialize s3 connection parameters
        """
        load_dotenv()
        self.fs = s3fs.S3FileSystem(
            client_kwargs={'endpoint_url': 'https://' + os.environ['AWS_S3_ENDPOINT']},
            key=os.environ["AWS_ACCESS_KEY_ID"],
            secret=os.environ["AWS_SECRET_ACCESS_KEY"],
            token=os.environ["AWS_SESSION_TOKEN"])
        bucket_name = 'maeldieudonne'
        self.destination = bucket_name + '/diffusion/'

    @staticmethod
    def get_latest_local_backup(table_name):
        """
        Check if other save files are present and select the newest
        """
        backup_files = [f for f in os.listdir("data/backups") if f.startswith(table_name)]

        if not backup_files:
            logger.info(f"No local backup found for {table_name}")
            return None

        else:
            latest_backup = max(backup_files, key=lambda f: os.path.getctime(os.path.join("data/backups", f)))
            file_path = os.path.join("data/backups", latest_backup)
            return file_path


    def upload_backup(self, file_path):
        try:
            self.fs.put(file_path, self.destination, content_type="parquet", encoding="utf-8")
            os.remove(file_path)
            logger.info(f"Successfully uploaded {file_path} to {self.destination}")
        except Exception as e:
            logger.error(f"Failed uploading {file_path} to {self.destination}: {e}")


    def clean_backup_directory(self):
        pattern = re.compile(r"([^/]+)_(\d{8}_\d{6})\.parquet$")

        # List all files
        files = self.fs.ls(self.destination)

        # Group by table name
        table_files = {}
        for file in files:
            match = pattern.search(file)
            if match:
                table_name, timestamp = match.groups()
                if table_name not in table_files:
                    table_files[table_name] = []
                table_files[table_name].append((file, timestamp))

        files_to_delete = []
        for table_name, file_list in table_files.items():
            file_list.sort(key=lambda x: x[1], reverse=True)  # Sort by timestamp (newest first)
            old_files = file_list[3:]  # Keep only 3 newest
            files_to_delete.extend([f[0] for f in old_files])

        if not files_to_delete:
            logger.info("No files to delete")
        else:
            logger.info(f"{len(files_to_delete)} files to delete")

        try:
            for file in files_to_delete:
                self.fs.rm(f"{'file'}")
                logger.info(f"Deleted {file}")
        except Exception as e:
            logger.error(f"Failed to remove files from S3: {e}")


    @staticmethod
    def extract_timestamp(file_name):
        match = re.search(r'(\d{8}_\d{6})', file_name)
        if match:
            return datetime.strptime(match.group(1), '%Y%m%d_%H%M%S')
        return None


    def load_latest_backup(self, table_name):
        # Look for a backup in S3
        all_files = [f['name'] for f in self.fs.listdir(self.destination)]
        backup_files = [f for f in all_files if f.startswith(f"{self.destination}{table_name}")]

        if not backup_files:
            # Look for sample data locally
            try:
                backup = pd.read_csv(f"data/sample/{table_name}.csv")
                logger.info(f"Loading sample data for {table_name}")
                return backup
            except:
                logger.warning(f"No distant or local backup found for {table_name}")

        else:
            file_path = max(backup_files, key=s3.extract_timestamp)
            timestamp = s3.extract_timestamp(file_path).strftime('%Y-%m-%d %H:%M:%S')
            with self.fs.open(f's3://{file_path}', 'rb') as f:
                backup = pd.read_parquet(f)
            logger.info(f"Loading distant backup for {table_name}: {timestamp}")
            return backup
