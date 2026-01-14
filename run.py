"""
Application entry point.
Initializes Firebase config, database, cache, and starts the Flask application.
"""
import sys
import logging

from src.config import init_firebase_config, setup_logging, Config
from src.services.db_service import init_database
from src.services.cache_service import init_cache
from src.services.cleanup_service import init_cleanup
from src.app import create_app

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    try:
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
            # See deployment instructions
            logger.info("Running in production mode. Use gunicorn to start the server.")
            return app
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
