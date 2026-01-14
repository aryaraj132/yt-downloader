"""Cleanup service for automatic video file deletion."""
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from src.config import Config
from src.models.video import Video

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up expired video files."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def cleanup_expired_videos(self):
        """Delete expired video files and update database."""
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
                
                # Delete file from filesystem
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted expired video file: {file_path}")
                    except OSError as e:
                        logger.error(f"Failed to delete file {file_path}: {str(e)}")
                
                # Update database to remove file_path
                from src.services.db_service import get_database
                from bson import ObjectId
                db = get_database()
                db.videos.update_one(
                    {'_id': ObjectId(video_id)},
                    {
                        '$set': {
                            'file_path': None,
                            'status': 'expired'
                        }
                    }
                )
                
                deleted_count += 1
            
            logger.info(f"Cleanup completed: {deleted_count} video(s) processed")
            
        except Exception as e:
            logger.error(f"Cleanup task error: {str(e)}")
    
    def cleanup_failed_sessions(self):
        """Cleanup expired sessions from database."""
        try:
            from src.models.session import Session
            deleted_count = Session.cleanup_expired()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")
    
    def start(self):
        """Start the cleanup scheduler."""
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
        """Stop the cleanup scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Cleanup service stopped")


# Global cleanup service instance
cleanup_service = CleanupService()


def init_cleanup() -> CleanupService:
    """Initialize and start cleanup service."""
    cleanup_service.start()
    return cleanup_service


def get_cleanup() -> CleanupService:
    """Get the cleanup service instance."""
    return cleanup_service
