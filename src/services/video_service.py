"""Video processing service using yt-dlp."""
import os
import sys
import logging
import subprocess
import re
import time
from typing import Optional, Tuple, Dict, Callable
from datetime import datetime
import uuid

from src.config import Config
from src.utils.validators import sanitize_filename
from src.models.video import Video, VideoStatus
from src.services import ffmpeg_utils_service

logger = logging.getLogger(__name__)


class VideoService:
    """Service for downloading and processing YouTube videos (pure logic, no database).
    
    This service contains only business logic. For database operations, use VideoData layer.
    \"\"\"
    
    @staticmethod
    def download_video_segment(
        url: str,
        start_time: int,
        end_time: int,
        output_path: str,
        format_preference: str = 'webm',
        resolution_preference: str = 'best',
        video_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download video segment using yt-dlp (database-agnostic).
        
        Args:
            url: YouTube video URL
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Path for output file
            format_preference: Format (mp4, webm, best)
            resolution_preference: Resolution (1080p, 720p, best)
            video_id: Optional video ID for cache storage
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, file_path, error_message)
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get FFmpeg location
            ffmpeg_path, ffmpeg_dir = ffmpeg_utils_service.get_ffmpeg_path()
            if not ffmpeg_path or not ffmpeg_dir:
                return False, None, "FFmpeg not available"
            
            # Build format selection string
            format_string = VideoService._build_format_string(resolution_preference, format_preference)
            
            # Build yt-dlp command
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                url,
                '-f', format_string,
                '--merge-output-format', format_preference if format_preference != 'best' else 'mp4',
                '--download-sections', f'*{start_time}-{end_time}',
                '-o', output_path,
                '--no-playlist',
                '--newline',
                '--progress',
            ]
            
            # Add FFmpeg location
            env = os.environ.copy()
            env['PATH'] = ffmpeg_dir + os.pathsep + env.get('PATH', '')
            
            logger.info(f"Starting download: {url} ({start_time}-{end_time}s)")
            
            # Execute yt-dlp with progress monitoring
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            last_update = 0
            current_phase = "Initializing"
            
            for line in process.stdout:
                line = line.strip()
                
                # Parse download progress
                if '[download]' in line and '%' in line:
                    now = time.time()
                    if now - last_update >= 0.3:
                        last_update = now
                        
                        # Extract progress info
                        percent_match = re.search(r'(\d+\.\d+)%', line)
                        size_match = re.search(r'of\s+~?(\S+)', line)
                        speed_match = re.search(r'at\s+(\S+/s)', line)
                        eta_match = re.search(r'ETA\s+(\S+)', line)
                        
                        if percent_match:
                            progress_data = {
                                'percent': float(percent_match.group(1)),
                                'size': size_match.group(1) if size_match else "unknown",
                                'speed': speed_match.group(1) if speed_match else "?",
                                'eta': eta_match.group(1) if eta_match else "?",
                                'phase': current_phase
                            }
                            
                            # Store in cache if video_id provided
                            if video_id:
                                from src.services.progress_cache import ProgressCache
                                ProgressCache.set_progress(video_id, {
                                    'download_progress': progress_data['percent'],
                                    'current_phase': 'downloading',
                                    'speed': progress_data['speed'],
                                    'eta': progress_data['eta']
                                })
                            
                            # Call user callback if provided
                            if progress_callback:
                                progress_callback(progress_data)
                
                # Track phase changes
                elif '[download]' in line and 'Destination:' in line:
                    current_phase = "Downloading"
                elif '[Merger]' in line or 'Merging' in line.lower():
                    current_phase = "Merging"
                    if video_id:
                        from src.services.progress_cache import ProgressCache
                        ProgressCache.update_field(video_id, 'current_phase', 'merging')
                    if progress_callback:
                        progress_callback({'phase': 'Merging', 'percent': 99})
            
            # Wait for process to complete
            process.wait()
            
            if process.returncode != 0:
                error_msg = f"yt-dlp failed (exit code {process.returncode})"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Verify file was created
            if not os.path.exists(output_path):
                error_msg = "Downloaded file not found"
                logger.error(error_msg)
                return False, None, error_msg
            
            logger.info(f"Download successful: {output_path}")
            return True, output_path, None
            
        except subprocess.TimeoutExpired:
            error_msg = "Download timeout"
            logger.error(f"Download timeout")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Download error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False, None, error_msg
    
    @staticmethod
    def _build_format_string(resolution: str, format_ext: str) -> str:
        """
        Build yt-dlp format selection string based on preferences.
        
        Args:
            resolution: Preferred resolution (e.g., '1080p', '720p', 'best')
            format_ext: Preferred format extension (e.g., 'mp4', 'webm', 'best')
            
        Returns:
            Format string for yt-dlp -f parameter
        """
        # Handle special cases
        if resolution == 'best' and format_ext == 'best':
            return 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        
        if resolution == 'best':
            if format_ext == 'mp4':
                return 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                return f'bestvideo[ext={format_ext}]+bestaudio/best[ext={format_ext}]/best'
        
        # Extract height from resolution
        if resolution.endswith('p'):
            try:
                height = int(resolution[:-1])
            except ValueError:
                height = None
        elif resolution.isdigit():
            height = int(resolution)
        else:
            height = None
        
        # Build format string with resolution constraint
        if height:
            if format_ext == 'mp4':
                return f'bestvideo[height<={height}][ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
            elif format_ext == 'best':
                return f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            else:
                return f'bestvideo[height<={height}][ext={format_ext}]+bestaudio/best[height<={height}][ext={format_ext}]/best'
        
        # Fallback
        return 'bestvideo+bestaudio/best'

    
    @staticmethod
    def get_video_info(url: str) -> Optional[Dict]:
        """
        Get video information using yt-dlp without downloading.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video metadata dict or None
        """
        try:
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                url,
                '--dump-json',
                '--no-playlist',
                '--no-warnings',
                '--quiet'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get video info: {result.stderr}")
                return None
            
            import json
            info = json.loads(result.stdout)
            
            return {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader')
            }
            
        except Exception as e:
            logger.error(f"Get video info error: {str(e)}")
            return None
