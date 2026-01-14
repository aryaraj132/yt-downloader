"""
Application startup script with FFmpeg setup.
This is the main entrypoint for starting the server.
"""
import sys
import logging
from pathlib import Path

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_and_setup_ffmpeg():
    """Check if FFmpeg is available, set it up if not."""
    logger.info("Checking FFmpeg setup...")
    
    try:
        from setup_ffmpeg import verify_ffmpeg, setup_ffmpeg
        
        if verify_ffmpeg():
            logger.info("✓ FFmpeg is ready")
            return True
        
        logger.info("FFmpeg not found. Setting up...")
        
        if setup_ffmpeg():
            logger.info("✓ FFmpeg setup completed")
            return True
        else:
            logger.error("✗ FFmpeg setup failed")
            return False
            
    except Exception as e:
        logger.error(f"FFmpeg check failed: {str(e)}")
        return False


def start_server():
    """Start the Flask application server."""
    try:
        from src.config import init_firebase_config, setup_logging, Config
        from src.services.db_service import init_database
        from src.services.cache_service import init_cache
        from src.services.cleanup_service import init_cleanup
        from src.app import create_app
        
        # Setup logging
        logger.info("Setting up application logging...")
        setup_logging()
        
        # Initialize Firebase and load configuration
        logger.info("Initializing Firebase configuration...")
        init_firebase_config()
        
        # Initialize database
        logger.info("Connecting to MongoDB...")
        init_database()
        
        # Initialize Redis cache
        logger.info("Connecting to Redis...")
        init_cache()
        
        # Initialize cleanup service
        logger.info("Starting cleanup service...")
        init_cleanup()
        
        # Create Flask app
        logger.info("Creating Flask application...")
        app = create_app()
        
        # Start the application
        logger.info(f"Starting server on port {Config.PORT}...")
        logger.info(f"Environment: {Config.FLASK_ENV}")
        
        # Run with Flask development server or gunicorn in production
        if Config.FLASK_ENV == 'development':
            app.run(
                host='0.0.0.0',
                port=Config.PORT,
                debug=True
            )
        else:
            # In production, this script should be run with gunicorn
            # The app is returned for gunicorn to use
            logger.info("Running in production mode.")
            logger.info("Start with: gunicorn -c gunicorn_config.py 'start_server:create_application()'")
            return app
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)


def create_application():
    """
    Application factory for production WSGI servers.
    Called by gunicorn.
    """
    # Check FFmpeg first
    if not check_and_setup_ffmpeg():
        logger.error("Cannot start server without FFmpeg")
        sys.exit(1)
    
    # Import and initialize
    from src.config import init_firebase_config, setup_logging, Config
    from src.services.db_service import init_database
    from src.services.cache_service import init_cache
    from src.services.cleanup_service import init_cleanup
    from src.app import create_app
    
    setup_logging()
    init_firebase_config()
    init_database()
    init_cache()
    init_cleanup()
    
    return create_app()


def main():
    """Main entrypoint."""
    print("\n" + "="*60)
    print("YouTube Video Downloader - Server Startup")
    print("="*60 + "\n")
    
    # Step 1: Check and setup FFmpeg
    if not check_and_setup_ffmpeg():
        print("\n❌ FFmpeg setup failed. Cannot start server.")
        print("Please ensure 'imageio-ffmpeg' is installed:")
        print("  pip install imageio-ffmpeg")
        sys.exit(1)
    
    # Step 2: Start the server
    print("\n✓ Pre-flight checks passed. Starting server...\n")
    start_server()


if __name__ == '__main__':
    main()
