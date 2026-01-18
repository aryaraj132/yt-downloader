
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
    
    @staticmethod
    def download_video_segment(
        url: str,
        start_time: int,
        end_time: int,
        output_path: str,
        format_preference: str = 'mp4',
        resolution_preference: str = '1080p',
        video_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            ffmpeg_path, ffmpeg_dir = ffmpeg_utils_service.get_ffmpeg_path()
            if not ffmpeg_path or not ffmpeg_dir:
                return False, None, "FFmpeg not available"
            
            resolution_height = VideoService._extract_resolution_height(resolution_preference)
            needs_encoding = False
            temp_webm_path = None
            
            if resolution_height >= 1440 and format_preference == 'mp4':
                needs_encoding = True
                temp_webm_path = output_path.replace('.mp4', '_temp.webm')
                download_path = temp_webm_path
                actual_format = 'webm'
            else:
                download_path = output_path
                actual_format = format_preference
            
            format_string = VideoService._build_format_string(resolution_preference, actual_format)
            
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                url,
                '-f', format_string,
                '--merge-output-format', actual_format,
                '--download-sections', f'*{start_time}-{end_time}',
                '-o', download_path,
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
                
                if '[download]' in line and '%' in line:
                    now = time.time()
                    if now - last_update >= 0.3:
                        last_update = now
                        
                        percent_match = re.search(r'(\d+\.?\d*)%', line)
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
                            
                            if video_id:
                                from src.services.progress_cache import ProgressCache
                                ProgressCache.set_progress(video_id, {
                                    'download_progress': progress_data['percent'],
                                    'current_phase': 'downloading',
                                    'speed': progress_data['speed'],
                                    'eta': progress_data['eta']
                                })
                            
                            if progress_callback:
                                progress_callback(progress_data)
                
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
            
            if not os.path.exists(download_path):
                error_msg = "Downloaded file not found"
                logger.error(error_msg)
                return False, None, error_msg
            
            if needs_encoding:
                from src.services.encoding_service import EncodingService
                
                logger.info(f"Encoding {download_path} to {output_path}")
                
                success, error = EncodingService.encode_video_to_mp4(
                    download_path,
                    output_path,
                    video_codec='h265',
                    quality_preset='lossless',
                    use_gpu=True,
                    encode_id=video_id,
                    progress_callback=progress_callback
                )
                
                try:
                    if os.path.exists(download_path):
                        os.remove(download_path)
                        logger.info(f"Removed temp file: {download_path}")
                except Exception as e:
                    logger.warning(f"Could not remove temp file: {e}")
                
                if not success:
                    return False, None, f"Encoding failed: {error}"
                
                logger.info(f"Encoding successful: {output_path}")
                return True, output_path, None
            else:
                logger.info(f"Download successful: {output_path}")
                return True, download_path, None
            
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
    def _extract_resolution_height(resolution: str) -> int:

        if resolution in ['best', 'worst']:
            return 0
        
        match = re.search(r'(\d+)p?', resolution)
        if match:
            return int(match.group(1))
        
        return 0
    
    @staticmethod
    def _build_format_string(resolution: str, format_ext: str) -> str:
        
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
