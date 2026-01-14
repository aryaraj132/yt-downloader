"""Video model for managing video download requests."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from bson import ObjectId
from enum import Enum

from src.services.db_service import get_database
from src.config import Config

logger = logging.getLogger(__name__)


class VideoStatus(str, Enum):
    """Video processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Video:
    """Video model for managing download requests."""
    
    @staticmethod
    def create_video_info(user_id: str, url: str, start_time: int, end_time: int) -> Optional[str]:
        """
        Create a new video download request.
        
        Args:
            user_id: User ID as string
            url: YouTube video URL
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Video ID as string if successful, None otherwise
        """
        try:
            db = get_database()
            
            # Create video document
            video_doc = {
                'user_id': ObjectId(user_id),
                'url': url,
                'start_time': start_time,
                'end_time': end_time,
                'status': VideoStatus.PENDING,
                'file_path': None,
                'created_at': datetime.utcnow(),
                'expires_at': None,  # Will be set after download completes
                'error_message': None
            }
            
            result = db.videos.insert_one(video_doc)
            logger.info(f"Video info created for user {user_id}: {url}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create video info: {str(e)}")
            return None
    
    @staticmethod
    def find_by_id(video_id: str) -> Optional[Dict]:
        """
        Find video by ID.
        
        Args:
            video_id: Video ID as string
            
        Returns:
            Video document or None if not found
        """
        try:
            db = get_database()
            video = db.videos.find_one({'_id': ObjectId(video_id)})
            return video
            
        except Exception as e:
            logger.error(f"Failed to find video by ID: {str(e)}")
            return None
    
    @staticmethod
    def find_by_user(user_id: str, limit: int = 50) -> List[Dict]:
        """
        Find videos by user ID.
        
        Args:
            user_id: User ID as string
            limit: Maximum number of videos to return
            
        Returns:
            List of video documents
        """
        try:
            db = get_database()
            videos = list(db.videos.find(
                {'user_id': ObjectId(user_id)}
            ).sort('created_at', -1).limit(limit))
            return videos
            
        except Exception as e:
            logger.error(f"Failed to find videos by user: {str(e)}")
            return []
    
    @staticmethod
    def update_status(video_id: str, status: VideoStatus, file_path: Optional[str] = None, 
                     error_message: Optional[str] = None) -> bool:
        """
        Update video processing status.
        
        Args:
            video_id: Video ID as string
            status: New status
            file_path: Path to downloaded file (for completed status)
            error_message: Error message (for failed status)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = get_database()
            
            update_fields = {
                'status': status
            }
            
            if file_path:
                update_fields['file_path'] = file_path
                # Set expiration time when video is downloaded
                update_fields['expires_at'] = datetime.utcnow() + timedelta(
                    minutes=Config.VIDEO_RETENTION_MINUTES
                )
            
            if error_message:
                update_fields['error_message'] = error_message
            
            result = db.videos.update_one(
                {'_id': ObjectId(video_id)},
                {'$set': update_fields}
            )
            
            if result.modified_count > 0:
                logger.info(f"Video status updated to {status}: {video_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update video status: {str(e)}")
            return False
    
    @staticmethod
    def find_expired() -> List[Dict]:
        """
        Find all expired videos that need cleanup.
        
        Returns:
            List of expired video documents
        """
        try:
            db = get_database()
            videos = list(db.videos.find({
                'expires_at': {'$lte': datetime.utcnow()},
                'file_path': {'$ne': None}  # Only videos that have files
            }))
            return videos
            
        except Exception as e:
            logger.error(f"Failed to find expired videos: {str(e)}")
            return []
    
    @staticmethod
    def delete_video(video_id: str) -> bool:
        """
        Delete video document from database.
        
        Args:
            video_id: Video ID as string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = get_database()
            result = db.videos.delete_one({'_id': ObjectId(video_id)})
            
            if result.deleted_count > 0:
                logger.info(f"Video deleted: {video_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete video: {str(e)}")
            return False
    
    @staticmethod
    def verify_ownership(video_id: str, user_id: str) -> bool:
        """
        Verify that a video belongs to a specific user.
        
        Args:
            video_id: Video ID as string
            user_id: User ID as string
            
        Returns:
            True if user owns the video, False otherwise
        """
        try:
            video = Video.find_by_id(video_id)
            if not video:
                return False
            
            return str(video['user_id']) == user_id
            
        except Exception as e:
            logger.error(f"Failed to verify video ownership: {str(e)}")
            return False
