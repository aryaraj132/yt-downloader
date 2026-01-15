"""Video processing service using yt-dlp."""
import os
import logging
import subprocess
from typing import Optional, Tuple, Dict
from datetime import datetime
import uuid

from src.config import Config
from src.utils.validators import sanitize_filename
from src.models.video import Video, VideoStatus

logger = logging.getLogger(__name__)

# Setup FFmpeg from local bin directory or imageio-ffmpeg
def get_ffmpeg_location():
    """Get FFmpeg binary location."""
    # First check local bin directory (production)
    import os
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    bin_dir = project_root / 'bin'
    ffmpeg_path = bin_dir / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    
    if ffmpeg_path.exists():
        logger.info(f"Using FFmpeg from bin directory: {ffmpeg_path}")
        return str(bin_dir)
    
    # Fall back to imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        logger.info(f"Using FFmpeg from imageio-ffmpeg: {ffmpeg_dir}")
        return ffmpeg_dir
    except ImportError:
        logger.warning("FFmpeg not found in bin/ and imageio-ffmpeg not installed")
        return None

FFMPEG_LOCATION = get_ffmpeg_location()


class VideoService:
    """Service for downloading and processing YouTube videos."""
    
    @staticmethod
    def download_video(video_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download video segment using yt-dlp.
        
        Args:
            video_id: Video document ID
            
        Returns:
            Tuple of (success, file_path, error_message)
        """
        try:
            # Get video info from database
            video = Video.find_by_id(video_id)
            
            if not video:
                return False, None, "Video not found"
            
            if video['status'] == VideoStatus.COMPLETED:
                # Already downloaded
                return True, video.get('file_path'), None
            
            # Update status to processing
            Video.update_status(video_id, VideoStatus.PROCESSING)
            
            url = video['url']
            start_time = video['start_time']
            end_time = video['end_time']
            
            # Get format and resolution preferences
            format_pref = video.get('format_preference', Config.DEFAULT_VIDEO_FORMAT)
            resolution_pref = video.get('resolution_preference', Config.DEFAULT_VIDEO_RESOLUTION)
            
            # Generate unique filename with preferred extension
            file_ext = format_pref if format_pref != 'best' else 'mp4'
            filename = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.{file_ext}"
            output_path = os.path.join(Config.DOWNLOADS_DIR, filename)
            
            # Ensure downloads directory exists
            os.makedirs(Config.DOWNLOADS_DIR, exist_ok=True)
            
            # Calculate duration for segment
            duration = end_time - start_time
            
            # Build format selection string for yt-dlp
            # This respects both resolution and format preferences
            format_string = VideoService._build_format_string(resolution_pref, format_pref)
            
            # Build yt-dlp command
            cmd = [
                'yt-dlp',
                url,
                '-f', format_string,
                '--merge-output-format', file_ext,
                '--download-sections', f'*{start_time}-{end_time}',
                '-o', output_path,
                '--no-playlist',
                '--no-warnings',
                '--quiet',
                '--force-overwrites'
            ]
            
            # Add FFmpeg location if available
            if FFMPEG_LOCATION:
                cmd.insert(4, '--ffmpeg-location')
                cmd.insert(5, FFMPEG_LOCATION)
            
            logger.info(f"Starting video download: {url} ({start_time}-{end_time}s) format={format_pref} resolution={resolution_pref}")
            
            # Execute yt-dlp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "yt-dlp failed"
                logger.error(f"yt-dlp error: {error_msg}")
                Video.update_status(video_id, VideoStatus.FAILED, error_message=error_msg)
                return False, None, error_msg
            
            # Verify file was created
            if not os.path.exists(output_path):
                error_msg = "Downloaded file not found"
                logger.error(error_msg)
                Video.update_status(video_id, VideoStatus.FAILED, error_message=error_msg)
                return False, None, error_msg
            
            # Update status to completed
            Video.update_status(video_id, VideoStatus.COMPLETED, file_path=output_path)
            
            logger.info(f"Video downloaded successfully: {output_path}")
            return True, output_path, None
            
        except subprocess.TimeoutExpired:
            error_msg = "Download timeout"
            logger.error(f"Video download timeout: {video_id}")
            Video.update_status(video_id, VideoStatus.FAILED, error_message=error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Video download error: {error_msg}")
            Video.update_status(video_id, VideoStatus.FAILED, error_message=error_msg)
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
        
        # Extract height from resolution (e.g., '1080p' -> 1080)
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
                'yt-dlp',
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
