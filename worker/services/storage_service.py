"""
S3 storage service for the worker.
Handles uploading processed files and downloading source files for encoding.
"""
import os
import logging
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from config import Config

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Get or create S3 client."""
    global _client
    if _client is None:
        _client = boto3.client(
            's3',
            endpoint_url=Config.S3_ENDPOINT_URL or None,
            aws_access_key_id=Config.S3_ACCESS_KEY,
            aws_secret_access_key=Config.S3_SECRET_KEY,
            region_name=Config.S3_REGION,
            config=BotoConfig(s3={'addressing_style': 'path'}, signature_version='s3v4')
        )
        logger.info("S3 client initialized")
    return _client


def upload_file(file_path, object_name=None, content_type=None):
    """
    Upload a file to S3.
    Returns: (success, object_name_or_error)
    """
    s3 = get_client()
    if not s3:
        return False, "S3 client not initialized"

    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        logger.info(f"Uploading {file_path} to S3 as {object_name}")
        s3.upload_file(file_path, Config.S3_BUCKET_NAME, object_name, ExtraArgs=extra_args)
        return True, object_name

    except ClientError as e:
        error = f"S3 upload failed: {str(e)}"
        logger.error(error)
        return False, error
    except Exception as e:
        error = f"Upload error: {str(e)}"
        logger.error(error)
        return False, error


def download_file(object_name, local_path):
    """
    Download a file from S3 to local path.
    Returns: (success, error_message)
    """
    s3 = get_client()
    if not s3:
        return False, "S3 client not initialized"

    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        logger.info(f"Downloading {object_name} from S3 to {local_path}")
        s3.download_file(Config.S3_BUCKET_NAME, object_name, local_path)
        return True, None

    except ClientError as e:
        error = f"S3 download failed: {str(e)}"
        logger.error(error)
        return False, error
    except Exception as e:
        error = f"Download error: {str(e)}"
        logger.error(error)
        return False, error


def delete_file(object_name):
    """Delete a file from S3."""
    s3 = get_client()
    if not s3:
        return False

    try:
        logger.info(f"Deleting {object_name} from S3")
        s3.delete_object(Bucket=Config.S3_BUCKET_NAME, Key=object_name)
        return True
    except Exception as e:
        logger.error(f"S3 delete failed: {str(e)}")
        return False


def list_objects(prefix=''):
    """List objects in the S3 bucket with optional prefix."""
    s3 = get_client()
    if not s3:
        return []

    try:
        response = s3.list_objects_v2(
            Bucket=Config.S3_BUCKET_NAME,
            Prefix=prefix
        )
        return response.get('Contents', [])
    except Exception as e:
        logger.error(f"S3 list objects failed: {str(e)}")
        return []
