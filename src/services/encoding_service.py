"""Video encoding service using FFmpeg.

This service provides functionality to encode/convert various video formats
to MP4 with configurable codecs and quality settings.
"""
import os
import logging
import subprocess
import json
import re
from typing import Optional, Tuple, Dict
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.models.video import Video, VideoStatus

logger = logging.getLogger(__name__)


# Codec configurations with quality presets
CODEC_CONFIGS = {
    'h264': {
        'encoder': 'libx264',
        'quality_presets': {
            'lossless': {'crf': '18', 'preset': 'slow'},
            'high': {'crf': '23', 'preset': 'medium'},
            'medium': {'crf': '28', 'preset': 'fast'}
        }
    },
    'h265': {
        'encoder': 'libx265',
        'quality_presets': {
            'lossless': {'crf': '20', 'preset': 'slow'},
            'high': {'crf': '25', 'preset': 'medium'},
            'medium': {'crf': '30', 'preset': 'fast'}
        }
    },
    'av1': {
        'encoder': 'libaom-av1',
        'quality_presets': {
            'lossless': {'crf': '15', 'cpu-used': '4'},
            'high': {'crf': '30', 'cpu-used': '4'},
            'medium': {'crf': '35', 'cpu-used': '6'}
        }
    }
}

# Audio encoding configuration
AUDIO_CONFIG = {
    'codec': 'aac',
    'bitrate': '192k',  # High quality AAC audio
    'sample_rate': '48000'
}


def get_ffmpeg_location():
    """Get FFmpeg binary location."""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    bin_dir = project_root / 'bin'
    ffmpeg_path = bin_dir / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    
    if ffmpeg_path.exists():
        logger.info(f"Using FFmpeg from bin directory: {ffmpeg_path}")
        return str(ffmpeg_path)
    
    # Fall back to imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info(f"Using FFmpeg from imageio-ffmpeg: {ffmpeg_exe}")
        return ffmpeg_exe
    except ImportError:
        logger.warning("FFmpeg not found in bin/ and imageio-ffmpeg not installed")
        return None


FFMPEG_PATH = get_ffmpeg_location()


class EncodingService:
    """Service for encoding videos to MP4 with various codecs."""
    
    @staticmethod
    def validate_video_file(file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a file is a valid video.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, "File not found"
        
        if not FFMPEG_PATH:
            return False, "FFmpeg not available"
        
        try:
            # Use ffprobe to check if file is a valid video
            cmd = [
                FFMPEG_PATH.replace('ffmpeg', 'ffprobe') if 'ffmpeg' in FFMPEG_PATH else 'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'json',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "Invalid video file or unsupported format"
            
            data = json.loads(result.stdout)
            if not data.get('streams'):
                return False, "No video stream found in file"
            
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "Validation timeout"
        except Exception as e:
            logger.error(f"Video validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def get_video_metadata(file_path: str) -> Optional[Dict]:
        """
        Extract video metadata using ffprobe.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dictionary containing video metadata or None
        """
        if not FFMPEG_PATH:
            logger.error("FFmpeg not available")
            return None
        
        try:
            ffprobe_path = FFMPEG_PATH.replace('ffmpeg', 'ffprobe') if 'ffmpeg' in FFMPEG_PATH else 'ffprobe'
            
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration,size:stream=codec_name,codec_type,width,height,bit_rate',
                '-of', 'json',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                logger.error(f"ffprobe error: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # Extract relevant information
            metadata = {
                'duration': float(data.get('format', {}).get('duration', 0)),
                'size_bytes': int(data.get('format', {}).get('size', 0)),
            }
            
            # Find video and audio streams
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    metadata['video_codec'] = stream.get('codec_name')
                    metadata['width'] = stream.get('width')
                    metadata['height'] = stream.get('height')
                    metadata['video_bitrate'] = stream.get('bit_rate')
                elif stream.get('codec_type') == 'audio':
                    metadata['audio_codec'] = stream.get('codec_name')
                    metadata['audio_bitrate'] = stream.get('bit_rate')
            
            return metadata
            
        except Exception as e:
            logger.error(f"Get metadata error: {str(e)}")
            return None
    
    @staticmethod
    def encode_video_to_mp4(
        input_path: str,
        output_path: str,
        video_codec: str = 'h264',
        quality_preset: str = 'high',
        encode_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Encode video to MP4 format with specified codec and quality.
        
        Args:
            input_path: Path to input video file
            output_path: Path for output MP4 file
            video_codec: Video codec (h264, h265, av1)
            quality_preset: Quality preset (lossless, high, medium)
            encode_id: Optional encode request ID for progress updates
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not FFMPEG_PATH:
                return False, "FFmpeg not available"
            
            # Validate codec and preset
            if video_codec not in CODEC_CONFIGS:
                return False, f"Unsupported codec: {video_codec}"
            
            codec_config = CODEC_CONFIGS[video_codec]
            if quality_preset not in codec_config['quality_presets']:
                return False, f"Invalid quality preset: {quality_preset}"
            
            preset_config = codec_config['quality_presets'][quality_preset]
            encoder = codec_config['encoder']
            
            # Build FFmpeg command
            cmd = [
                FFMPEG_PATH,
                '-i', input_path,
                '-c:v', encoder,
                '-c:a', AUDIO_CONFIG['codec'],
                '-b:a', AUDIO_CONFIG['bitrate'],
                '-ar', AUDIO_CONFIG['sample_rate'],
            ]
            
            # Add codec-specific parameters
            if video_codec == 'av1':
                cmd.extend(['-crf', preset_config['crf']])
                cmd.extend(['-cpu-used', preset_config['cpu-used']])
                cmd.extend(['-row-mt', '1'])  # Enable row-based multithreading for AV1
            else:
                cmd.extend(['-crf', preset_config['crf']])
                cmd.extend(['-preset', preset_config['preset']])
            
            # Output settings
            cmd.extend([
                '-movflags', '+faststart',  # Enable fast start for web playback
                '-pix_fmt', 'yuv420p',  # Ensure compatibility
                '-y',  # Overwrite output file
                output_path
            ])
            
            logger.info(f"Starting encoding: {video_codec} ({quality_preset})")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            # Update status to processing
            if encode_id:
                Video.update_status(encode_id, VideoStatus.PROCESSING)
            
            # Execute FFmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # Monitor progress
            duration = None
            for line in process.stderr:
                # Extract duration from FFmpeg output
                if duration is None:
                    duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
                    if duration_match:
                        hours, minutes, seconds = duration_match.groups()
                        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                
                # Extract current time for progress calculation
                time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
                if time_match and duration and encode_id:
                    hours, minutes, seconds = time_match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    progress = min(int((current_time / duration) * 100), 99)
                    
                    # Update progress in database
                    from src.services.db_service import get_database
                    db = get_database()
                    db.videos.update_one(
                        {'_id': Video.find_by_id(encode_id)['_id']},
                        {'$set': {'encoding_progress': progress}}
                    )
            
            # Wait for process to complete
            process.wait(timeout=Config.ENCODING_TIMEOUT_SECONDS)
            
            if process.returncode != 0:
                error_output = process.stderr.read() if process.stderr else "Unknown error"
                logger.error(f"Encoding failed: {error_output}")
                return False, f"Encoding failed: {error_output[:200]}"
            
            # Verify output file exists
            if not os.path.exists(output_path):
                return False, "Output file not created"
            
            logger.info(f"Encoding completed successfully: {output_path}")
            return True, None
            
        except subprocess.TimeoutExpired:
            error_msg = f"Encoding timeout (max: {Config.ENCODING_TIMEOUT_SECONDS}s)"
            logger.error(error_msg)
            if process:
                process.kill()
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Encoding error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def get_supported_codecs() -> Dict[str, list]:
        """
        Get list of supported codecs and quality presets.
        
        Returns:
            Dictionary mapping codec names to their available presets
        """
        return {
            codec: list(config['quality_presets'].keys())
            for codec, config in CODEC_CONFIGS.items()
        }
