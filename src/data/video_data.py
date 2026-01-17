"""Video data layer - handles database operations for video downloads.

This layer sits between routes and services:
- Routes call data layer methods
- Data layer fetches/updates database
- Data layer calls pure service methods
- Services contain only business logic
"""
import os
import logging
from typing import Optional, Tuple
from datetime import datetime
import uuid

from src.config import Config
from src.models.video import Video, VideoStatus
from src.services.video_service import VideoService

logger = logging.getLogger(__name__)


class VideoData:
    """Data layer for video download operations."""
    
    @staticmethod
    def download_video(
        video_id: str,
        format_preference: str = None,
        resolution_preference: str = None,
        progress_callback=None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download video using database info (for API).
        
        Args:
            video_id: Video document ID
            format_preference: Optional format (mp4, webm, best)
            resolution_preference: Optional resolution (1080p, 720p, best)
            progress_callback: Optional progress callback
            
        Returns:
            Tuple of (success, file_path, error_message)
        """
        try:
            # Fetch from database
            video = Video.find_by_id(video_id)
            
            if not video:
                return False, None, "Video not found"
            
            if video['status'] == VideoStatus.COMPLETED:
                return True, video.get('file_path'), None
            
            # Update status to processing
            Video.update_status(video_id, VideoStatus.PROCESSING)
            
            # Extract parameters
            url = video['url']
            start_time = video['start_time']
            end_time = video['end_time']
            
            # Use provided preferences or defaults
            format_pref = format_preference or Config.DEFAULT_VIDEO_FORMAT
            resolution_pref = resolution_preference or Config.DEFAULT_VIDEO_RESOLUTION
            
            # Generate output path
            file_ext = format_pref if format_pref != 'best' else 'mp4'
            filename = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.{file_ext}"
            output_path = os.path.join(Config.DOWNLOADS_DIR, filename)
            os.makedirs(Config.DOWNLOADS_DIR, exist_ok=True)
            
            # Call service (pure logic, no database)
            success, file_path, error = VideoService.download_video_segment(
                url=url,
                start_time=start_time,
                end_time=end_time,
                output_path=output_path,
                format_preference=format_pref,
                resolution_preference=resolution_pref,
                video_id=video_id,  # For cache storage
                progress_callback=progress_callback
            )
            
            # Update database with result
            if success:
                Video.update_status(video_id, VideoStatus.COMPLETED, file_path=file_path)
                return True, file_path, None
            else:
                Video.update_status(video_id, VideoStatus.FAILED, error_message=error)
                return False, None, error
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Video download error: {error_msg}")
            Video.update_status(video_id, VideoStatus.FAILED, error_message=error_msg)
            return False, None, error_msg
