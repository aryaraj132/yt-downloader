"""
Test script to download and encode video in multiple resolutions and formats.

Expected output:
- 3 webm files (720p, 1080p, 1440p) - downloaded directly
- 6 mp4 files:
  - 3 from webm encoding (720p, 1080p, 1440p)
  - 3 from direct mp4 download (720p, 1080p, 1440p)
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.services.video_service import VideoService
from src.services.encoding_service import EncodingService
import time


# Configuration
VIDEO_URL = "https://www.youtube.com/watch?v=RQDCbgn2vDM"
START_TIME_STR = "0:10:20"
END_TIME_STR = "0:14:20"
RESOLUTIONS = ["2160p"]
FORMATS = ["mp4"]
CODEC = 'av1'
QUALITY = 'lossless'

# Convert times
from src.services import ffmpeg_utils_service
START_TIME = ffmpeg_utils_service.timestamp_to_seconds(START_TIME_STR)
END_TIME = ffmpeg_utils_service.timestamp_to_seconds(END_TIME_STR)

# Output directory
DOWNLOADS_DIR = script_dir / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)


def download_and_process(url, start, end, resolution, format_ext):
    
    timestamp = int(datetime.now().timestamp())
    output_file = DOWNLOADS_DIR / f"{resolution}_{format_ext}_{timestamp}.{format_ext}"
    
    print("\n" + "=" * 80)
    print(f"Processing: {resolution} ({format_ext})")
    print("=" * 80)
    print(f"\nDownloading {resolution} in {format_ext} format...")
    
    def progress_callback(data):
        if 'percent' in data:
            percent = data.get('percent', 0)
            speed = data.get('speed', '?')
            eta = data.get('eta', '?')
            
            bar_width = 40
            filled = int(bar_width * percent / 100)
            bar = '█' * filled + '░' * (bar_width - filled)
            
            print(f"\r[{bar}] {percent:.1f}% | {speed} | ETA: {eta}", end='', flush=True)
    
    success, file_path, error = VideoService.download_video_segment(
        url=url,
        start_time=start,
        end_time=end,
        output_path=str(output_file),
        format_preference=format_ext,
        resolution_preference=resolution,
        video_id=None,
        progress_callback=progress_callback
    )
    
    print()
    
    if not success:
        print(f"❌ Download failed: {error}")
        return False
    
    if os.path.exists(file_path):
        size_mb = os.path.getsize(file_path) / (1024*1024)
        print(f"✅ Success: {os.path.basename(file_path)} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"❌ File not found: {file_path}")
        return False


def main():
    print("\n" + "=" * 80)
    print("Multi-Resolution & Format Download Test")
    print("=" * 80)
    print(f"\nVideo: {VIDEO_URL}")
    print(f"Segment: {START_TIME_STR} to {END_TIME_STR} ({END_TIME - START_TIME} seconds)")
    print(f"Resolutions: {', '.join(RESOLUTIONS)}")
    print(f"Formats: {', '.join(FORMATS)}")
    print(f"\nExpected output:")
    print(f"  - {len(RESOLUTIONS)} webm files")
    print(f"  - {len(RESOLUTIONS) * 2} mp4 files (direct + encoded)")
    print(f"  - Total: {len(RESOLUTIONS) * len(FORMATS) + len(RESOLUTIONS)} files")
    
    results = []
    start_time = time.time()
    
    # Process each combination
    for resolution in RESOLUTIONS:
        for format_ext in FORMATS:
            success = download_and_process(
                VIDEO_URL,
                START_TIME,
                END_TIME,
                resolution,
                format_ext
            )
            
            results.append({
                'resolution': resolution,
                'format': format_ext,
                'success': success
            })
            
            # Small delay between downloads
            if success:
                time.sleep(1)
    
    # Summary
    elapsed = int(time.time() - start_time)
    
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"\nCompleted in {elapsed//60}m {elapsed%60}s")
    print(f"\nResults:")
    
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['resolution']:>6} ({r['format']})")
    
    print(f"\nSuccess: {successful}/{len(results)}")
    print(f"Failed:  {failed}/{len(results)}")
    
    # List all files created
    print(f"\nFiles in {DOWNLOADS_DIR}:")
    files = sorted(DOWNLOADS_DIR.glob("*.*"))
    
    webm_files = [f for f in files if f.suffix == '.webm']
    mp4_files = [f for f in files if f.suffix == '.mp4']
    
    print(f"\n  WebM files ({len(webm_files)}):")
    for f in webm_files:
        size_mb = f.stat().st_size / (1024*1024)
        print(f"    - {f.name} ({size_mb:.2f} MB)")
    
    print(f"\n  MP4 files ({len(mp4_files)}):")
    for f in mp4_files:
        size_mb = f.stat().st_size / (1024*1024)
        print(f"    - {f.name} ({size_mb:.2f} MB)")
    
    print("\n" + "=" * 80)
    
    if successful == len(results):
        print("🎉 All downloads and encodings completed successfully!")
    else:
        print(f"⚠️  {failed} task(s) failed")
    
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
