import pytest
from src.utils.s3 import s3


def test_s3_initialization():
    try:
        s3_client = s3()
    except Exception as e:
        pytest.fail(f"S3 initialization failed: {e}")
