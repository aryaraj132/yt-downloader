"""
Test script - Download ONLY a specific segment.
Creates a wrapper script so yt-dlp can find FFmpeg.
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime


def timestamp_to_seconds(timestamp):
    """
    Convert timestamp in format 'hr:min:sec' to seconds.
    Also accepts 'min:sec' or just 'sec'.
    
    Examples:
        '1:44:00' -> 6240
        '44:00' -> 2640
        '90' -> 90
    """
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


# Test parameters
TEST_URL = "https://www.youtube.com/live/fRdMGjcqczM"
START_TIME_STR = "1:14:45"  # Can use format like "1:44:00" or "0:1:30"
END_TIME_STR = "3:12:40"    # Automatically converts to seconds
START_TIME = timestamp_to_seconds(START_TIME_STR)
END_TIME = timestamp_to_seconds(END_TIME_STR)
TIMEOUT = max(300, END_TIME - START_TIME * 2)
# Output
DOWNLOADS_DIR = "./downloads"
OUTPUT_PATH = os.path.join(DOWNLOADS_DIR, f"segment_{int(datetime.now().timestamp())}.mp4")


def setup_ffmpeg():
    """Setup FFmpeg so yt-dlp can find it."""
    try:
        import imageio_ffmpeg
        ffmpeg_source = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Create a local bin directory
        local_bin = os.path.join(os.getcwd(), 'bin')
        os.makedirs(local_bin, exist_ok=True)
        
        ffmpeg_dest = os.path.join(local_bin, 'ffmpeg.exe')
        ffprobe_dest = os.path.join(local_bin, 'ffprobe.exe')  # Some versions need this
        
        # Copy FFmpeg to local bin if not already there
        if not os.path.exists(ffmpeg_dest):
            shutil.copy2(ffmpeg_source, ffmpeg_dest)
            print(f"✓ Copied FFmpeg to {ffmpeg_dest}")
        else:
            print(f"✓ FFmpeg already in {ffmpeg_dest}")
        
        #  Also copy ffprobe if it exists
        ffprobe_source = ffmpeg_source.replace('ffmpeg', 'ffprobe')
        if os.path.exists(ffprobe_source) and not os.path.exists(ffprobe_dest):
            shutil.copy2(ffprobe_source, ffprobe_dest)
            print(f"✓ Copied ffprobe to {ffprobe_dest}")
        
        # Test it
        result = subprocess.run([ffmpeg_dest, '-version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ FFmpeg is working!")
            return local_bin
        
        return None
        
    except Exception as e:
        print(f"✗ FFmpeg setup error: {e}")
        return None


def test_download(ffmpeg_dir):
    """Download segment using yt-dlp."""
    print("\n" + "="*70)
    print("YouTube Segment Download Test")
    print("="*70)
    print(f"\nDownloading ONLY {END_TIME - START_TIME} seconds ({START_TIME_STR} to {END_TIME_STR})")
    print(f"Output: {OUTPUT_PATH}\n")
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    # Add FFmpeg to PATH
    env = os.environ.copy()
    env['PATH'] = ffmpeg_dir + os.pathsep + env.get('PATH', '')
    
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        TEST_URL,
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        '--merge-output-format', 'mp4',
        '--download-sections', f'*{START_TIME}-{END_TIME}',
        '-o', OUTPUT_PATH,
        '--no-playlist',
    ]
    
    print("Starting download...\n")
    print("Progress will be shown below:")
    print("-" * 70 + "\n")
    
    try:
        # Don't capture output - let yt-dlp show progress in real-time
        result = subprocess.run(cmd, env=env, timeout=TIMEOUT)
        
        print("\n" + "-" * 70)
        
        if result.returncode != 0:
            print(f"\n✗ Download failed (exit code {result.returncode})")
            return False
        
        if os.path.exists(OUTPUT_PATH):
            size_mb = os.path.getsize(OUTPUT_PATH) / (1024*1024)
            print(f"✅ SUCCESS!")
            print(f"\nFile: {os.path.abspath(OUTPUT_PATH)}")
            print(f"Size: {size_mb:.2f} MB")
            print(f"\nThis is ONLY the 60-second segment!")
            return True
        
        print("✗ File not created")
        return False
        
    except subprocess.TimeoutExpired:
        print("✗ Timeout")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("\nYouTube Segment Downloader - Test")
    print("Downloads ONLY the specified segment\n")
    
    ffmpeg_dir = setup_ffmpeg()
    if not ffmpeg_dir:
        print("\n❌ FFmpeg setup failed")
        sys.exit(1)
    
    success = test_download(ffmpeg_dir)
    
    print("\n" + "="*70)
    if success:
        print("✅ TEST PASSED - Segment downloaded successfully!")
    else:
        print("❌ TEST FAILED")
        sys.exit(1)
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
