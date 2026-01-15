"""Validation utilities for input data."""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, None


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for at least one digit, one letter
    has_digit = any(char.isdigit() for char in password)
    has_letter = any(char.isalpha() for char in password)
    
    if not (has_digit and has_letter):
        return False, "Password must contain both letters and numbers"
    
    return True, None


def validate_youtube_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate YouTube URL format.
    
    Args:
        url: YouTube URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is required"
    
    # YouTube URL patterns
    patterns = [
        r'(https?://)?(www\.)?(youtube\.com/watch\?v=[\w-]+)',
        r'(https?://)?(www\.)?(youtu\.be/[\w-]+)',
        r'(https?://)?(www\.)?(youtube\.com/embed/[\w-]+)',
        r'(https?://)?(www\.)?(youtube\.com/v/[\w-]+)',
    ]
    
    for pattern in patterns:
        if re.search(pattern, url):
            return True, None
    
    return False, "Invalid YouTube URL"


def validate_time_range(start_time: int, end_time: int, max_duration: int) -> Tuple[bool, Optional[str]]:
    """
    Validate video time range.
    
    Args:
        start_time: Start time in seconds
        end_time: End time in seconds
        max_duration: Maximum allowed duration in seconds
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if start_time < 0:
        return False, "Start time must be non-negative"
    
    if end_time <= start_time:
        return False, "End time must be greater than start time"
    
    duration = end_time - start_time
    
    if duration > max_duration:
        return False, f"Duration exceeds maximum allowed ({max_duration} seconds)"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove invalid characters for filenames
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    
    # Limit filename length
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized or 'video'


def validate_video_id(video_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate YouTube video ID format.
    
    Args:
        video_id: Video ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not video_id:
        return False, "Video ID is required"
    
    if not isinstance(video_id, str):
        return False, "Video ID must be a string"
    
    # YouTube video IDs are 11 characters: alphanumeric, underscore, hyphen
    pattern = r'^[a-zA-Z0-9_-]{11}$'
    
    if not re.match(pattern, video_id):
        return False, "Invalid video ID format"
    
    return True, None


def validate_format_preference(format_pref: str) -> Tuple[bool, Optional[str]]:
    """
    Validate video format preference.
    
    Args:
        format_pref: Preferred video format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not format_pref:
        return True, None  # Format is optional
    
    # Supported formats for yt-dlp
    supported_formats = [
        'mp4', 'webm', 'mkv', 'flv', 'avi', 
        'm4a', 'mp3', 'ogg', 'wav', 'best'
    ]
    
    format_lower = format_pref.lower()
    
    if format_lower not in supported_formats:
        return False, f"Unsupported format. Supported formats: {', '.join(supported_formats)}"
    
    return True, None


def validate_resolution_preference(resolution: str) -> Tuple[bool, Optional[str]]:
    """
    Validate video resolution preference.
    
    Args:
        resolution: Preferred resolution (e.g., "1080p", "720p", "best")
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not resolution:
        return True, None  # Resolution is optional
    
    # Common resolution options
    supported_resolutions = [
        'best', 'worst',
        '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p',
        '4320p',  # 8K
    ]
    
    resolution_lower = resolution.lower()
    
    # Check if it's a supported resolution string
    if resolution_lower in supported_resolutions:
        return True, None
    
    # Check if it's a custom height value (e.g., "1080" or "720")
    if resolution.isdigit():
        height = int(resolution)
        if 144 <= height <= 4320:
            return True, None
        return False, "Resolution height must be between 144 and 4320"
    
    return False, f"Unsupported resolution. Examples: {', '.join(supported_resolutions[:8])}"

