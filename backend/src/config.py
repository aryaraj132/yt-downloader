"""
Configuration loader for YouTube Downloader application.
Loads environment variables and initializes Firebase Admin SDK.
"""
import os
import logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials

# Load .env file for local development
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables."""
    
    # Firebase
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH', '../firebase-service-account.json')
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'yt-downloader')
    
    # Redis
    REDIS_URI = os.getenv('REDIS_URI', 'redis://localhost:6379/0')
    
    # JWT
    JWT_PUBLIC_SECRET = os.getenv('JWT_PUBLIC_SECRET', 'default-public-secret')
    JWT_PRIVATE_SECRET = os.getenv('JWT_PRIVATE_SECRET', 'default-private-secret')
    # Public tokens don't expire - they're permanent keys stored in user DB
    JWT_PRIVATE_EXPIRATION = int(os.getenv('JWT_PRIVATE_EXPIRATION', 31536000))  # 7 days default

    
    # Flask
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    PORT = int(os.getenv('PORT', 5000))
    
    # Application
    DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', './downloads')
    UPLOADS_DIR = os.getenv('UPLOADS_DIR', './uploads')
    MAX_VIDEO_DURATION = int(os.getenv('MAX_VIDEO_DURATION', 3600))  # 1 hour
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', 500))  # 500MB
    VIDEO_RETENTION_MINUTES = int(os.getenv('VIDEO_RETENTION_MINUTES', 30))
    CLEANUP_INTERVAL_MINUTES = int(os.getenv('CLEANUP_INTERVAL_MINUTES', 5))
    ENCODING_TIMEOUT_SECONDS = int(os.getenv('ENCODING_TIMEOUT_SECONDS', 1800))  # 30 minutes
    ALLOWED_VIDEO_FORMATS = os.getenv(
        'ALLOWED_VIDEO_FORMATS',
        'mp4,avi,mkv,mov,flv,wmv,webm,m4v,mpg,mpeg,3gp'
    ).split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/app.log')
    
    # Video Download Preferences
    DEFAULT_VIDEO_FORMAT = os.getenv('DEFAULT_VIDEO_FORMAT', 'mp4')
    DEFAULT_VIDEO_RESOLUTION = os.getenv('DEFAULT_VIDEO_RESOLUTION', 'best')
    SUPPORTED_FORMATS = ['mp4', 'webm', 'mkv', 'flv', 'avi', 'm4a', 'mp3', 'ogg', 'wav', 'best']
    SUPPORTED_RESOLUTIONS = ['best', 'worst', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p', '4320p']
    
    # YouTube API (Optional - for metadata fetching if needed)
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')  # Optional, not used with OAuth

    # Google OAuth Configuration
    # Required scopes for YouTube Data API access:
    # - https://www.googleapis.com/auth/youtube.readonly (read video/stream info)
    # - https://www.googleapis.com/auth/youtube.force-ssl (read live chat)
    # - https://www.googleapis.com/auth/userinfo.email (get user email)
    # - openid (OAuth standard)
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')

    # Public API Configuration
    PUBLIC_API_RATE_LIMIT = int(os.getenv('PUBLIC_API_RATE_LIMIT', 10))  # Operations per day
    PUBLIC_API_MAX_CLIP_DURATION = int(os.getenv('PUBLIC_API_MAX_CLIP_DURATION', 40))  # Seconds
    PUBLIC_API_MAX_ENCODE_DURATION = int(os.getenv('PUBLIC_API_MAX_ENCODE_DURATION', 300))  # 5 minutes in seconds

    
    @classmethod
    def validate(cls):
        """Validate that all required configuration values are set."""
        required_vars = [
            'MONGODB_URI',
            'MONGODB_URI',
            # 'JWT_PUBLIC_SECRET',  # Not required with OAuth
            # 'JWT_PRIVATE_SECRET', # Not required with OAuth
            'FLASK_SECRET_KEY',
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        
        logger.info("Configuration validated successfully")
        return True


def init_firebase_config():
    """
    Initialize Firebase Admin SDK and load remote config.
    This should be called before starting the application.
    """
    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Initialize Firebase Admin SDK
            if Config.FIREBASE_SERVICE_ACCOUNT_KEY_PATH and os.path.exists(
                Config.FIREBASE_SERVICE_ACCOUNT_KEY_PATH
            ):
                cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
                
                # Note: Firebase Remote Config is typically used for client apps
                # For server-side config, we're using environment variables
                # If you want to use Firebase Remote Config, you can implement it here
            else:
                logger.warning(
                    "Firebase service account key not found. "
                    "Skipping Firebase initialization. "
                    "Using environment variables only."
                )
        
        # Validate configuration
        Config.validate()
        
        # Create necessary directories
        os.makedirs(Config.DOWNLOADS_DIR, exist_ok=True)
        os.makedirs(Config.UPLOADS_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(Config.LOG_FILE) if os.path.dirname(Config.LOG_FILE) else './logs', exist_ok=True)
        
        logger.info("Configuration initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase config: {str(e)}")
        raise


def setup_logging():
    """Configure application logging."""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    logger.info(f"Logging configured with level: {Config.LOG_LEVEL}")
