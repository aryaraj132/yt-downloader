"""
Test script - Download ONLY a specific segment.
Creates a wrapper script so yt-dlp can find FFmpeg.
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime

# Test parameters
TEST_URL = "https://www.youtube.com/watch?v=5e9uIk3CC3A"
START_TIME = 6240  # 1:44:00
END_TIME = 6300    # 1:45:00

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
    print(f"\nDownloading ONLY 60 seconds (1:44:00 to 1:45:00)")
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
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"✗ Failed (exit code {result.returncode})")
            print("\nError:")
            print(result.stderr[-500:])  # Last 500 chars
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
