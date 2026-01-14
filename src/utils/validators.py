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
