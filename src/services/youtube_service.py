
import logging
import re
from typing import Optional, Dict, Tuple
import subprocess
import json

logger = logging.getLogger(__name__)

class YouTubeService:
    
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
        
        if not video_id:
            return False, "Video ID cannot be empty"
        
        if not isinstance(video_id, str):
            return False, "Video ID must be a string"
        
        if not YouTubeService.VIDEO_ID_PATTERN.match(video_id):
            return False, "Invalid video ID format. Must be 11 characters (alphanumeric, underscore, hyphen)"
        
        return True, None
    
    @staticmethod
    def parse_video_id_from_url(url: str) -> Optional[str]:
        
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
        
        return f"https://www.youtube.com/watch?v={video_id}"
    
    @staticmethod
    def get_video_info(video_id: str, cookies_content: Optional[str] = None) -> Optional[Dict]:
        
        cookies_file = None
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

            if cookies_content:
                import uuid
                import time
                import os
                # Create detailed timestamped filename to avoid collisions - ideally this should be a utility method
                cookies_filename = f"cookies_info_{uuid.uuid4()}_{int(time.time())}.txt"
                # Use a temp directory or app root for these temporary files
                cookies_file = os.path.join(os.getcwd(), cookies_filename)
                
                # Write cookies to file
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    f.write(cookies_content)
                
                # securely pass cookies to yt-dlp
                cmd.extend(['--cookies', cookies_file])
            
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
        finally:
            if cookies_file and os.path.exists(cookies_file):
                try:
                    os.remove(cookies_file)
                except Exception:
                    pass
    
    @staticmethod
    def get_available_formats(video_id: str, cookies_content: Optional[str] = None) -> Optional[list]:
        
        cookies_file = None
        try:
            import sys
            import uuid
            import time
            import os
            
            url = YouTubeService.construct_video_url(video_id)
            
            # Use yt-dlp to get video info with formats
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                '--dump-json',
                '--no-warnings',
                '--skip-download',
                url
            ]

            if cookies_content:
                # Create detailed timestamped filename to avoid collisions
                cookies_filename = f"cookies_fmt_{uuid.uuid4()}_{int(time.time())}.txt"
                cookies_file = os.path.join(os.getcwd(), cookies_filename)
                
                # Write cookies to file
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    f.write(cookies_content)
                
                # securely pass cookies to yt-dlp
                cmd.extend(['--cookies', cookies_file])
            
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
            
            # Collect unique resolutions >= 720p
            resolutions = set()
            
            for fmt in formats:
                height = fmt.get('height')
                
                if height and height >= 720:
                    resolution = f"{height}p"
                    resolutions.add(resolution)
            
            # Return sorted list (highest first)
            if resolutions:
                return sorted(list(resolutions), key=lambda x: int(x[:-1]), reverse=True)
            else:
                return None
            
        except Exception as e:
            logger.error(f"Failed to get available formats: {str(e)}")
            return None
        finally:
            if cookies_file and os.path.exists(cookies_file):
                try:
                    os.remove(cookies_file)
                except Exception:
                    pass
