"""
Configuration for the YouTube Downloader Worker.
Loads environment variables for Redis, MongoDB, S3, queue, and Firebase settings.

IMPORTANT: bootstrap.py must run BEFORE this module is imported
so that Firebase Remote Config values are available in os.environ.
"""
import os
from pathlib import Path


class Config:
    """Worker configuration from environment variables."""

    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI', '')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'yt-downloader')

    # Redis
    REDIS_URI = os.getenv('REDIS_URI', 'redis://localhost:6379/0')

    # S3 / SeaweedFS
    S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL', '')
    S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
    S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')
    S3_REGION = os.getenv('S3_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'yt-downloader')
    S3_KEY_PREFIX = os.getenv('S3_KEY_PREFIX', 'videos/')

    # Queue names (must match API server)
    QUEUE_DOWNLOAD = os.getenv('QUEUE_DOWNLOAD', 'queue:download')
    QUEUE_ENCODE = os.getenv('QUEUE_ENCODE', 'queue:encode')

    # Worker settings
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY_SECONDS = int(os.getenv('RETRY_DELAY_SECONDS', '30'))
    TEMP_DIR = os.getenv('TEMP_DIR', './tmp')
    CLEANUP_INTERVAL_HOURS = int(os.getenv('CLEANUP_INTERVAL_HOURS', '1'))
    S3_FILE_MAX_AGE_HOURS = int(os.getenv('S3_FILE_MAX_AGE_HOURS', '24'))

    # Cookie file
    COOKIES_DIR = os.getenv('COOKIES_DIR', os.path.join(os.path.dirname(__file__), 'cookiesFile'))
    COOKIES_FILENAME = 'cookies.txt'

    # Video defaults
    DEFAULT_VIDEO_FORMAT = os.getenv('DEFAULT_VIDEO_FORMAT', 'mp4')
    DEFAULT_VIDEO_RESOLUTION = os.getenv('DEFAULT_VIDEO_RESOLUTION', 'best')

    # Firebase / Remote Config
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'local')
    SERVICE_ACCOUNT_JSON = os.getenv('SERVICE_ACCOUNT_JSON', '')
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv(
        'FIREBASE_SERVICE_ACCOUNT_KEY_PATH', 'firebase-service-account.json'
    )

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def get_cookies_path(cls):
        """Return the full path to the cookies file, or None if it doesn't exist."""
        cookies_path = os.path.join(cls.COOKIES_DIR, cls.COOKIES_FILENAME)
        if os.path.exists(cookies_path):
            return cookies_path
        return None

    @classmethod
    def validate(cls):
        """Validate required config."""
        required = ['MONGODB_URI', 'REDIS_URI']
        missing = [var for var in required if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
