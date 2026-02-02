"""
Validation service for public API endpoints.
Validates video durations and parameters.
"""
import logging
from typing import Tuple
from src.config import Config

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating public API requests."""
    
    @staticmethod
    def validate_clip_duration(start_time: int, end_time: int, is_public: bool = False) -> Tuple[bool, str]:
        """
        Validate video clip duration.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            is_public: Whether this is a public API request
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if start_time < 0:
                return (False, "Start time cannot be negative")
            
            if end_time <= start_time:
                return (False, "End time must be greater than start time")
            
            duration = end_time - start_time
            
            if is_public:
                # Public API: max 40 seconds
                if duration > Config.PUBLIC_API_MAX_CLIP_DURATION:
                    return (False, f"Public API clips are limited to {Config.PUBLIC_API_MAX_CLIP_DURATION} seconds. Please sign in for longer clips.")
            else:
                # Authenticated: use general max duration limit
                if duration > Config.MAX_VIDEO_DURATION:
                    return (False, f"Clip duration cannot exceed {Config.MAX_VIDEO_DURATION} seconds")
            
            return (True, "")
            
        except Exception as e:
            logger.error(f"Error validating clip duration: {str(e)}")
            return (False, "Invalid duration parameters")
    
    @staticmethod
    def validate_upload_duration(duration: float, is_public: bool = False) -> Tuple[bool, str]:
        """
        Validate uploaded video duration.
        
        Args:
            duration: Video duration in seconds
            is_public: Whether this is a public API request
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if duration <= 0:
                return (False, "Invalid video duration")
            
            if is_public:
                # Public API: max 5 minutes
                if duration > Config.PUBLIC_API_MAX_ENCODE_DURATION:
                    minutes = Config.PUBLIC_API_MAX_ENCODE_DURATION // 60
                    return (False, f"Public API encoding is limited to {minutes} minutes. Please sign in for longer videos.")
            else:
                # Authenticated: use general max duration limit
                if duration > Config.MAX_VIDEO_DURATION:
                    return (False, f"Video duration cannot exceed {Config.MAX_VIDEO_DURATION} seconds")
            
            return (True, "")
            
        except Exception as e:
            logger.error(f"Error validating upload duration: {str(e)}")
            return (False, "Invalid duration")
    
    @staticmethod
    def validate_youtube_url(url: str) -> Tuple[bool, str]:
        """
        Basic validation for YouTube URLs.
        
        Args:
            url: YouTube URL
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not url:
                return (False, "URL is required")
            
            # Basic check for YouTube domains
            valid_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
            is_youtube = any(domain in url.lower() for domain in valid_domains)
            
            if not is_youtube:
                return (False, "Invalid YouTube URL")
            
            return (True, "")
            
        except Exception as e:
            logger.error(f"Error validating YouTube URL: {str(e)}")
            return (False, "Invalid URL format")
