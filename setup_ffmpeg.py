"""
FFmpeg setup utility for production deployment.
Ensures FFmpeg is available before starting the server.
"""
import os
import sys
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_ffmpeg(force=False):
    """
    Setup FFmpeg in local bin directory using imageio-ffmpeg.
    
    Args:
        force: If True, re-setup even if already exists
        
    Returns:
        bool: True if setup successful
    """
    try:
        import imageio_ffmpeg
        
        # Define local bin directory
        project_root = Path(__file__).parent
        bin_dir = project_root / 'bin'
        ffmpeg_dest = bin_dir / 'ffmpeg.exe' if os.name == 'nt' else bin_dir / 'ffmpeg'
        ffprobe_dest = bin_dir / 'ffprobe.exe' if os.name == 'nt' else bin_dir / 'ffprobe'
        
        # Check if already setup
        if ffmpeg_dest.exists() and not force:
            logger.info(f"✓ FFmpeg already configured at {ffmpeg_dest}")
            return True
        
        # Create bin directory
        bin_dir.mkdir(exist_ok=True)
        logger.info(f"Created bin directory: {bin_dir}")
        
        # Get FFmpeg from imageio-ffmpeg
        ffmpeg_source = Path(imageio_ffmpeg.get_ffmpeg_exe())
        
        # Copy FFmpeg
        if ffmpeg_source.exists():
            shutil.copy2(ffmpeg_source, ffmpeg_dest)
            logger.info(f"✓ Copied FFmpeg to {ffmpeg_dest}")
            
            # Make executable on Unix systems
            if os.name != 'nt':
                os.chmod(ffmpeg_dest, 0o755)
        else:
            logger.error(f"✗ FFmpeg source not found: {ffmpeg_source}")
            return False
        
        # Copy ffprobe if available
        ffprobe_source = ffmpeg_source.parent / ('ffprobe.exe' if os.name == 'nt' else 'ffprobe')
        if ffprobe_source.exists():
            shutil.copy2(ffprobe_source, ffprobe_dest)
            logger.info(f"✓ Copied ffprobe to {ffprobe_dest}")
            if os.name != 'nt':
                os.chmod(ffprobe_dest, 0o755)
        
        # Verify setup
        import subprocess
        result = subprocess.run([str(ffmpeg_dest), '-version'], 
                              capture_output=True, timeout=5)
        
        if result.returncode == 0:
            version = result.stdout.decode().split('\n')[0]
            logger.info(f"✓ FFmpeg verified: {version}")
            return True
        else:
            logger.error("✗ FFmpeg verification failed")
            return False
            
    except ImportError:
        logger.error("✗ imageio-ffmpeg not installed. Run: pip install imageio-ffmpeg")
        return False
    except Exception as e:
        logger.error(f"✗ FFmpeg setup error: {str(e)}")
        return False


def get_ffmpeg_path():
    """
    Get path to FFmpeg binary.
    
    Returns:
        Path or None: Path to FFmpeg binary if available
    """
    project_root = Path(__file__).parent
    bin_dir = project_root / 'bin'
    ffmpeg_path = bin_dir / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    
    if ffmpeg_path.exists():
        return ffmpeg_path
    
    return None


def verify_ffmpeg():
    """
    Verify FFmpeg is available and working.
    
    Returns:
        bool: True if FFmpeg is ready to use
    """
    ffmpeg_path = get_ffmpeg_path()
    
    if not ffmpeg_path:
        logger.warning("FFmpeg not found in bin directory")
        return False
    
    try:
        import subprocess
        result = subprocess.run([str(ffmpeg_path), '-version'], 
                              capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"FFmpeg verification failed: {str(e)}")
        return False


if __name__ == '__main__':
    # Setup logging for manual execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("FFmpeg Setup Utility")
    print("=" * 50)
    
    if setup_ffmpeg():
        print("\n✅ FFmpeg setup completed successfully!")
        ffmpeg_path = get_ffmpeg_path()
        print(f"FFmpeg location: {ffmpeg_path}")
    else:
        print("\n❌ FFmpeg setup failed!")
        sys.exit(1)
