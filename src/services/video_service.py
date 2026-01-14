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
            
            # Generate unique filename
            filename = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.mp4"
            output_path = os.path.join(Config.DOWNLOADS_DIR, filename)
            
            # Ensure downloads directory exists
            os.makedirs(Config.DOWNLOADS_DIR, exist_ok=True)
            
            # Calculate duration for segment
            duration = end_time - start_time
            
            # Build yt-dlp command
            # Format: download video with h264 codec and aac audio, extract segment
            cmd = [
                'yt-dlp',
                url,
                '-f', 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
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
            
            logger.info(f"Starting video download: {url} ({start_time}-{end_time}s)")
            
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
