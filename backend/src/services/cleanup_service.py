
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from src.config import Config
from src.models.video import Video

logger = logging.getLogger(__name__)

class CleanupService:

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def cleanup_expired_videos(self):

        try:
            logger.info("Running cleanup task for expired videos")

            # Find all expired videos
            expired_videos = Video.find_expired()

            if not expired_videos:
                logger.debug("No expired videos found")
                return

            deleted_count = 0

            for video in expired_videos:
                video_id = str(video['_id'])
                file_path = video.get('file_path')
                input_file_path = video.get('input_file_path')

                # Delete output file from filesystem or S3
                storage_mode = video.get('storage_mode', 'local')

                if storage_mode == 's3' and file_path:
                    from src.services.storage_service import StorageService
                    if StorageService.delete_file(file_path):
                         logger.info(f"Deleted expired video from S3: {file_path}")
                    else:
                         logger.error(f"Failed to delete expired video from S3: {file_path}")
                elif file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted expired video file: {file_path}")
                    except OSError as e:
                        logger.error(f"Failed to delete file {file_path}: {str(e)}")

                # Delete input file from filesystem (for uploaded videos)
                if input_file_path and os.path.exists(input_file_path):
                    try:
                        os.remove(input_file_path)
                        logger.info(f"Deleted expired input file: {input_file_path}")
                    except OSError as e:
                        logger.error(f"Failed to delete input file {input_file_path}: {str(e)}")

                # Update database to remove file_path
                from src.services.db_service import get_database
                from bson import ObjectId
                db = get_database()
                db.videos.update_one(
                    {'_id': ObjectId(video_id)},
                    {
                        '$set': {
                            'file_path': None,
                            'input_file_path': None,
                            'status': 'expired'
                        }
                    }
                )

                deleted_count += 1

            logger.info(f"Cleanup completed: {deleted_count} video(s) processed")

        except Exception as e:
            logger.error(f"Cleanup task error: {str(e)}")

    def cleanup_failed_sessions(self):

        try:
            from src.models.session import Session
            deleted_count = Session.cleanup_expired()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")

        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")

    def start(self):

        if self.is_running:
            logger.warning("Cleanup service is already running")
            return

        try:
            # Schedule video cleanup every N minutes
            self.scheduler.add_job(
                self.cleanup_expired_videos,
                'interval',
                minutes=Config.CLEANUP_INTERVAL_MINUTES,
                id='cleanup_videos',
                replace_existing=True
            )

            # Schedule session cleanup every hour
            self.scheduler.add_job(
                self.cleanup_failed_sessions,
                'interval',
                hours=1,
                id='cleanup_sessions',
                replace_existing=True
            )

            self.scheduler.start()
            self.is_running = True

            logger.info(f"Cleanup service started (interval: {Config.CLEANUP_INTERVAL_MINUTES} minutes)")

        except Exception as e:
            logger.error(f"Failed to start cleanup service: {str(e)}")
            raise

    def stop(self):

        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Cleanup service stopped")

# Global cleanup service instance
cleanup_service = CleanupService()

def init_cleanup() -> CleanupService:

    cleanup_service.start()
    return cleanup_service

def get_cleanup() -> CleanupService:

    return cleanup_service
