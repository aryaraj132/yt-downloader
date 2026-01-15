"""YouTube service for video ID validation and metadata extraction."""
import logging
import re
from typing import Optional, Dict, Tuple
import subprocess
import json

logger = logging.getLogger(__name__)


class YouTubeService:
    """Service for YouTube-specific operations."""
    
    # YouTube video ID format: 11 characters, alphanumeric, underscore, and hyphen
    VIDEO_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    
    # URL patterns for extracting video IDs
    URL_PATTERNS = [
        re.compile(r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})'),
        re.compile(r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})'),
        re.compile(r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})'),
    ]
    
    @staticmethod
    def validate_video_id(video_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate YouTube video ID format.
        
        Args:
            video_id: Video ID string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not video_id:
            return False, "Video ID cannot be empty"
        
        if not isinstance(video_id, str):
            return False, "Video ID must be a string"
        
        if not YouTubeService.VIDEO_ID_PATTERN.match(video_id):
            return False, "Invalid video ID format. Must be 11 characters (alphanumeric, underscore, hyphen)"
        
        return True, None
    
    @staticmethod
    def parse_video_id_from_url(url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID if found, None otherwise
        """
        if not url:
            return None
        
        # Try each URL pattern
        for pattern in YouTubeService.URL_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)
        
        # Check if the URL itself is just a video ID
        is_valid, _ = YouTubeService.validate_video_id(url)
        if is_valid:
            return url
        
        return None
    
    @staticmethod
    def construct_video_url(video_id: str) -> str:
        """
        Build standard YouTube URL from video ID.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Full YouTube URL
        """
        return f"https://www.youtube.com/watch?v={video_id}"
    
    @staticmethod
    def get_video_info(video_id: str) -> Optional[Dict]:
        """
        Fetch video metadata using yt-dlp.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video metadata or None if failed
        """
        try:
            # Validate video ID first
            is_valid, error = YouTubeService.validate_video_id(video_id)
            if not is_valid:
                logger.error(f"Invalid video ID: {error}")
                return None
            
            url = YouTubeService.construct_video_url(video_id)
            
            # Use yt-dlp to get video info without downloading
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--skip-download',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                return None
            
            # Parse JSON output
            info = json.loads(result.stdout)
            
            # Extract relevant metadata
            metadata = {
                'video_id': info.get('id'),
                'title': info.get('title'),
                'duration': info.get('duration'),  # in seconds
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count'),
                'is_live': info.get('is_live', False),
                'was_live': info.get('was_live', False),
                'resolution': info.get('resolution'),
                'formats_available': len(info.get('formats', []))
            }
            
            logger.info(f"Retrieved metadata for video {video_id}: {metadata.get('title')}")
            return metadata
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while fetching video info for {video_id}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse yt-dlp JSON output: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            return None
    
    @staticmethod
    def get_available_formats(video_id: str) -> Optional[Dict]:
        """
        Get available formats and resolutions for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with available formats grouped by resolution
        """
        try:
            url = YouTubeService.construct_video_url(video_id)
            
            # Use yt-dlp to list formats
            cmd = [
                'yt-dlp',
                '--list-formats',
                '--dump-json',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                return None
            
            # Parse the JSON output
            info = json.loads(result.stdout)
            formats = info.get('formats', [])
            
            # Group formats by resolution and extension
            format_groups = {}
            resolutions = set()
            extensions = set()
            
            for fmt in formats:
                ext = fmt.get('ext', 'unknown')
                height = fmt.get('height')
                
                if height:
                    resolution = f"{height}p"
                    resolutions.add(resolution)
                    extensions.add(ext)
                    
                    if resolution not in format_groups:
                        format_groups[resolution] = []
                    
                    format_groups[resolution].append({
                        'format_id': fmt.get('format_id'),
                        'ext': ext,
                        'resolution': resolution,
                        'vcodec': fmt.get('vcodec', 'none'),
                        'acodec': fmt.get('acodec', 'none'),
                        'filesize': fmt.get('filesize'),
                        'tbr': fmt.get('tbr')  # total bitrate
                    })
            
            return {
                'video_id': video_id,
                'resolutions': sorted(list(resolutions), key=lambda x: int(x[:-1]), reverse=True),
                'extensions': sorted(list(extensions)),
                'formats': format_groups
            }
            
        except Exception as e:
            logger.error(f"Failed to get available formats: {str(e)}")
            return None
