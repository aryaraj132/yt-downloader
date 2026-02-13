"""
Test script - Download ONLY a specific segment.
Uses shared services for FFmpeg setup and utilities.
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.services import ffmpeg_utils_service


# Test parameters
TEST_URL = "https://www.youtube.com/watch?v=5135omtMu40"
START_TIME_STR = "1:08:57"  # Can use format like "1:44:00" or "0:1:30"
END_TIME_STR = "1:10:27"   # Automatically converts to seconds
START_TIME = ffmpeg_utils_service.timestamp_to_seconds(START_TIME_STR)
END_TIME = ffmpeg_utils_service.timestamp_to_seconds(END_TIME_STR)
TIMEOUT = max(300, END_TIME - START_TIME * 2)

# Output
DOWNLOADS_DIR = "./downloads"
OUTPUT_PATH = os.path.join(DOWNLOADS_DIR, f"segment_{int(datetime.now().timestamp())}.mp4")


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
        '-f', 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]',
        '--merge-output-format', 'webm',
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
            print(f"\nThis is ONLY the {END_TIME - START_TIME}-second segment!")
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
    
    # Setup FFmpeg using shared service
    print("=" * 70)
    print("Setting up FFmpeg...")
    print("=" * 70)
    
    ffmpeg_path, ffmpeg_dir = ffmpeg_utils_service.setup_ffmpeg()
    
    if not ffmpeg_path or not ffmpeg_dir:
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
