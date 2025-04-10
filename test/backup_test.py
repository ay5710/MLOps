import os
import pytest
import s3fs

from dotenv import load_dotenv


def test_s3():
    try:
        load_dotenv()
        fs = s3fs.S3FileSystem(
            client_kwargs={'endpoint_url': 'https://' + os.environ['AWS_S3_ENDPOINT']},
            key=os.environ["AWS_ACCESS_KEY_ID"],
            secret=os.environ["AWS_SECRET_ACCESS_KEY"],
            token=os.environ["AWS_SESSION_TOKEN"])
        bucket_name = 'maeldieudonne'
        destination = bucket_name + '/diffusion/'
        fs.put("data/sample/movies.csv", destination, content_type="csv", encoding="utf-8")
        fs.rm(f"{destination} + movies.csv")
    except Exception as e:
        pytest.fail(f"s3 failed: {e}")
