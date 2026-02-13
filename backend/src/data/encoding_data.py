"""Encoding data layer - handles database operations for video encoding.

This layer sits between routes and services:
- Routes call data layer methods
- Data layer fetches/updates database
- Data layer calls pure service methods
- Services contain only business logic
"""
import os
import logging
from typing import Optional, Tuple

from src.models.video import Video, VideoStatus
from src.services.encoding_service import EncodingService

logger = logging.getLogger(__name__)


class EncodingData:
    """Data layer for video encoding operations."""
    
    @staticmethod
    def encode_video(video_id: str, codec: str = 'h264', quality: str = 'high', progress_callback=None) -> Tuple[bool, Optional[str]]:
        """
        Encode video using database info (for API).
        
        Args:
            video_id: Video document ID
            codec: Video codec
            quality: Quality preset
            progress_callback: Optional progress callback
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Fetch from database
            video = Video.find_by_id(video_id)
            
            if not video:
                return False, "Video not found"
            
            input_path = video.get('file_path')
            if not input_path or not os.path.exists(input_path):
                return False, "Input file not found"
            
            # Update status
            Video.update_status(video_id, VideoStatus.PROCESSING)
            
            # Generate output path
            output_path = input_path.replace(os.path.splitext(input_path)[1], f'_encoded_{codec}.mp4')
            
            # Call service (pure logic, no database)
            success, error = EncodingService.encode_video_to_mp4(
                input_path=input_path,
                output_path=output_path,
                video_codec=codec,
                quality_preset=quality,
                use_gpu=True,
                encode_id=video_id,  # For cache storage
                progress_callback=progress_callback
            )
            
            # Update database with result
            if success:
                Video.update_status(video_id, VideoStatus.COMPLETED, file_path=output_path)
                return True, None
            else:
                Video.update_status(video_id, VideoStatus.FAILED, error_message=error)
                return False, error
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Video encoding error: {error_msg}")
            Video.update_status(video_id, VideoStatus.FAILED, error_message=error_msg)
            return False, error_msg
