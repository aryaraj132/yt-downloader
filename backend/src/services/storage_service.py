
import os
import logging
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from typing import Optional, Tuple

from src.config import Config

logger = logging.getLogger(__name__)

class StorageService:
    """Service for interacting with SeaweedFS S3 storage."""

    _client = None

    @classmethod
    def get_client(cls):
        """Get or create S3 client."""
        if cls._client is None:
            try:
                cls._client = boto3.client(
                    's3',
                    endpoint_url=Config.S3_ENDPOINT_URL,
                    aws_access_key_id=Config.S3_ACCESS_KEY,
                    aws_secret_access_key=Config.S3_SECRET_KEY,
                    region_name=Config.S3_REGION,
                    config=BotoConfig(s3={'addressing_style': 'path'}, signature_version='s3v4')
                )

                # Ensure bucket exists
                try:
                    cls._client.head_bucket(Bucket=Config.S3_BUCKET_NAME)
                except ClientError:
                    # Create bucket if it doesn't exist
                    try:
                        cls._client.create_bucket(Bucket=Config.S3_BUCKET_NAME)
                        logger.info(f"Created S3 bucket: {Config.S3_BUCKET_NAME}")
                    except Exception as e:
                        logger.error(f"Failed to create S3 bucket: {str(e)}")

            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
                return None

        return cls._client

    @staticmethod
    def upload_file(
        file_path: str,
        object_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Upload a file to SeaweedFS S3.

        Args:
            file_path: Path to local file
            object_name: S3 object name (defaults to filename)
            content_type: MIME type of file

        Returns:
            Tuple of (success, error_message/object_url)
        """
        s3 = StorageService.get_client()
        if not s3:
            return False, "S3 client not initialized"

        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            logger.info(f"Uploading {file_path} to S3 bucket {Config.S3_BUCKET_NAME} as {object_name}")

            s3.upload_file(
                file_path,
                Config.S3_BUCKET_NAME,
                object_name,
                ExtraArgs=extra_args
            )

            # Construct URL (not presigned, just the direct path if public or internal usage)
            # But for restricted buckets we should use presigned URLs.
            # SeaweedFS usually serves files publicly if configured.
            # We'll return the object key for now.

            return True, object_name

        except ClientError as e:
            error = f"S3 upload failed: {str(e)}"
            logger.error(error)
            return False, error
        except Exception as e:
            error = f"Upload error: {str(e)}"
            logger.error(error)
            return False, error

    @staticmethod
    def delete_file(object_name: str) -> bool:
        """
        Delete a file from SeaweedFS S3.

        Args:
            object_name: S3 object name

        Returns:
            True if successful, False otherwise
        """
        s3 = StorageService.get_client()
        if not s3:
            return False

        try:
            logger.info(f"Deleting {object_name} from S3 bucket {Config.S3_BUCKET_NAME}")
            s3.delete_object(Bucket=Config.S3_BUCKET_NAME, Key=object_name)
            return True

        except ClientError as e:
            logger.error(f"S3 delete failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Delete error: {str(e)}")
            return False

    @staticmethod
    def get_presigned_url(object_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL to share an S3 object.

        Args:
            object_name: S3 object name
            expiration: Time in seconds for the presigned URL to remain valid

        Returns:
            Presigned URL as string. If error, returns None.
        """
        s3 = StorageService.get_client()
        if not s3:
            return None

        try:
            response = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': Config.S3_BUCKET_NAME,
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
            return response

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Presigned URL error: {str(e)}")
            return None
