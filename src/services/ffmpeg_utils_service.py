
import os
import sys
import re
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def timestamp_to_seconds(timestamp) -> int:
    
    if isinstance(timestamp, (int, float)):
        return int(timestamp)
    
    parts = str(timestamp).split(':')
    
    if len(parts) == 3:  # hr:min:sec
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:  # min:sec
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    elif len(parts) == 1:  # just seconds
        return int(parts[0])
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")

def get_ffmpeg_path() -> Tuple[Optional[str], Optional[str]]:
    
    # Check project bin directory first
    project_root = Path(__file__).parent.parent.parent
    bin_dir = project_root / 'bin'
    ffmpeg_path = bin_dir / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    
    if ffmpeg_path.exists():
        logger.info(f"Using FFmpeg from bin directory: {ffmpeg_path}")
        return str(ffmpeg_path), str(bin_dir)
    
    # Fall back to imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = str(Path(ffmpeg_exe).parent)
        logger.info(f"Using FFmpeg from imageio-ffmpeg: {ffmpeg_dir}")
        return ffmpeg_exe, ffmpeg_dir
    except ImportError:
        logger.warning("FFmpeg not found in bin/ and imageio-ffmpeg not installed")
        return None, None

def setup_ffmpeg() -> Tuple[Optional[str], Optional[str]]:
    
    logger.info("Setting up FFmpeg...")
    
    ffmpeg_path, ffmpeg_dir = get_ffmpeg_path()
    
    if ffmpeg_path and os.path.exists(ffmpeg_path):
        logger.info(f"✅ FFmpeg found at: {ffmpeg_path}")
        
        # Test it
        try:
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("✅ FFmpeg is working!")
                return ffmpeg_path, ffmpeg_dir
        except Exception as e:
            logger.warning(f"⚠️  FFmpeg test failed: {e}")
    
    # Try to setup using imageio_ffmpeg
    try:
        import imageio_ffmpeg
        import shutil
        
        ffmpeg_source = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Create a local bin directory
        project_root = Path(__file__).parent.parent.parent
        local_bin = project_root / 'bin'
        local_bin.mkdir(exist_ok=True)
        
        ffmpeg_dest = local_bin / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
        
        # Copy FFmpeg to local bin if not already there
        if not ffmpeg_dest.exists():
            shutil.copy2(ffmpeg_source, ffmpeg_dest)
            logger.info(f"✓ Copied FFmpeg to {ffmpeg_dest}")
        
        # Test it
        result = subprocess.run(
            [str(ffmpeg_dest), '-version'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info("✅ FFmpeg setup complete!")
            return str(ffmpeg_dest), str(local_bin)
        
    except Exception as e:
        logger.error(f"❌ FFmpeg setup error: {e}")
        return None, None
    
    logger.error("❌ FFmpeg not available")
    return None, None

def get_video_duration(ffmpeg_path: str, video_path: str) -> Optional[float]:
    
    try:
        # ffprobe is usually in the same directory as ffmpeg
        ffprobe_path = str(Path(ffmpeg_path).parent / ('ffprobe.exe' if os.name == 'nt' else 'ffprobe'))
        
        # Try ffprobe first (fastest method)
        if os.path.exists(ffprobe_path):
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return float(result.stdout.strip())
                except ValueError:
                    pass
        
        # Fallback: Use FFmpeg to read metadata (NOT decode video)
        # Just running ffmpeg -i will output file info to stderr and exit
        cmd = [ffmpeg_path, '-i', str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Duration is in stderr (ffmpeg outputs metadata to stderr)
        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', result.stderr)
        if duration_match:
            hours, minutes, seconds = duration_match.groups()
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            
        return None
        
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️  Video duration check timed out (this shouldn't happen - may indicate a corrupted file)")
        return None
    except Exception as e:
        logger.warning(f"⚠️  Could not determine video duration: {e}")
        return None

def detect_gpu_encoder(ffmpeg_path: str, codec: str = 'h264') -> Tuple[Optional[str], Optional[str]]:
    
    encoders_to_test = []
    
    if codec == 'h264':
        # Test in order: AMD → NVIDIA → Intel
        encoders_to_test = [
            ('h264_amf', 'AMD'),
            ('h264_nvenc', 'NVIDIA'),
            ('h264_qsv', 'Intel QuickSync'),
        ]
    elif codec == 'h265':
        encoders_to_test = [
            ('hevc_amf', 'AMD'),
            ('hevc_nvenc', 'NVIDIA'),
            ('hevc_qsv', 'Intel QuickSync'),
        ]
    elif codec == 'av1':
        encoders_to_test = [
            ('av1_amf', 'AMD RDNA 3+'),
            ('av1_nvenc', 'NVIDIA RTX 40-series'),
            ('av1_qsv', 'Intel Arc'),
        ]
    
    # Test each encoder by trying to encode a dummy frame
    for encoder, gpu_type in encoders_to_test:
        try:
            # Create a test command that encodes 1 black frame
            cmd = [
                ffmpeg_path,
                '-f', 'lavfi',
                '-i', 'color=black:s=1280x720:d=0.1',
                '-c:v', encoder,
                '-frames:v', '1',
                '-f', 'null',
                '-'
            ]
            
            # Try to encode - if it works, this GPU encoder is available
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                # Encoder works! Return it
                logger.info(f"✅ Detected GPU encoder: {gpu_type} ({encoder})")
                return encoder, gpu_type
        except Exception:
            # This encoder doesn't work, try next one
            continue
    
    logger.info("ℹ️  No GPU encoder detected, will use CPU")
    return None, None
