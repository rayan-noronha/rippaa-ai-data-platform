"""S3 client for uploading documents to the landing bucket."""

import structlog
import boto3
from botocore.exceptions import ClientError

from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


def get_s3_client():
    """Create an S3 client pointing to LocalStack (dev) or real AWS (prod)."""
    settings = get_settings()
    kwargs = {
        "service_name": "s3",
        "region_name": settings.aws_region,
    }
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client(**kwargs)


def ensure_bucket_exists(bucket_name: str) -> None:
    """Create the S3 bucket if it doesn't exist (for LocalStack dev)."""
    settings = get_settings()
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.debug("Bucket already exists", bucket=bucket_name)
    except ClientError:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": settings.aws_region},
        )
        logger.info("Created S3 bucket", bucket=bucket_name)


def upload_file_to_s3(
    file_path: str,
    bucket: str,
    s3_key: str,
) -> str:
    """Upload a file to S3 and return the S3 key.

    Args:
        file_path: Local path to the file.
        bucket: S3 bucket name.
        s3_key: Destination key in S3.

    Returns:
        The S3 key where the file was uploaded.
    """
    s3 = get_s3_client()
    s3.upload_file(file_path, bucket, s3_key)
    logger.info("Uploaded file to S3", bucket=bucket, key=s3_key)
    return s3_key


def check_s3_health() -> bool:
    """Verify S3 connectivity."""
    try:
        s3 = get_s3_client()
        s3.list_buckets()
        return True
    except Exception:
        logger.exception("S3 health check failed")
        return False
