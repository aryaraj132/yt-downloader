"""
Worker entry point.
Starts queue consumers and cleanup scheduler in parallel threads.

Startup flow:
  1. Bootstrap (Firebase credentials, Remote Config, FFmpeg)
  2. Config validation
  3. Start download consumer, encode consumer, cleanup service
"""
import os
import sys
import logging
import threading
import signal

# Step 1: Bootstrap BEFORE importing Config
# (Remote Config values must be in os.environ before Config reads them)
from bootstrap import bootstrap
bootstrap()

from config import Config
from services.queue_consumer import QueueConsumer
from services.cleanup_service import CleanupService

# Set up logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

# Create temp directory
os.makedirs(Config.TEMP_DIR, exist_ok=True)

# Global flag for graceful shutdown
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()


def main():
    """Start the worker processes."""
    logger.info("=" * 60)
    logger.info("YouTube Downloader Worker Starting")
    logger.info("=" * 60)

    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Check cookies
    cookies_path = Config.get_cookies_path()
    if cookies_path:
        logger.info(f"Cookie file found: {cookies_path}")
    else:
        logger.info("No cookie file found, using default yt-dlp behavior")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create consumers
    download_consumer = QueueConsumer(
        queue_name=Config.QUEUE_DOWNLOAD,
        job_type='download',
        shutdown_event=shutdown_event,
    )

    encode_consumer = QueueConsumer(
        queue_name=Config.QUEUE_ENCODE,
        job_type='encode',
        shutdown_event=shutdown_event,
    )

    # Create cleanup service
    cleanup_service = CleanupService()

    # Start threads
    threads = []

    download_thread = threading.Thread(
        target=download_consumer.run,
        name='download-consumer',
        daemon=True,
    )
    threads.append(download_thread)

    encode_thread = threading.Thread(
        target=encode_consumer.run,
        name='encode-consumer',
        daemon=True,
    )
    threads.append(encode_thread)

    cleanup_thread = threading.Thread(
        target=cleanup_service.run,
        args=(shutdown_event,),
        name='cleanup-service',
        daemon=True,
    )
    threads.append(cleanup_thread)

    # Start all threads
    for t in threads:
        t.start()
        logger.info(f"Started thread: {t.name}")

    logger.info("Worker is running. Press Ctrl+C to stop.")

    # Wait for shutdown signal
    try:
        shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_event.set()

    logger.info("Waiting for threads to finish...")
    for t in threads:
        t.join(timeout=10)

    logger.info("Worker stopped.")


if __name__ == '__main__':
    main()
