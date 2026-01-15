"""
Combined YouTube Video Downloader and Encoder
Downloads a segment of a YouTube video and encodes it to high-quality MP4.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
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


def get_ffmpeg_path():
    """Get FFmpeg binary location."""
    # Check project bin directory first
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    bin_dir = project_root / 'bin'
    ffmpeg_path = bin_dir / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    
    if ffmpeg_path.exists():
        return str(ffmpeg_path), str(bin_dir)
    
    # Fall back to imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        return ffmpeg_exe, str(Path(ffmpeg_exe).parent)
    except ImportError:
        return None, None


def setup_ffmpeg():
    """Setup FFmpeg so yt-dlp can find it."""
    print("=" * 70)
    print("Setting up FFmpeg...")
    print("=" * 70)
    
    ffmpeg_path, ffmpeg_dir = get_ffmpeg_path()
    
    if ffmpeg_path and os.path.exists(ffmpeg_path):
        print(f"✅ FFmpeg found at: {ffmpeg_path}")
        
        # Test it
        try:
            result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                print("✅ FFmpeg is working!")
                return ffmpeg_path, ffmpeg_dir
        except Exception as e:
            print(f"⚠️  FFmpeg test failed: {e}")
    
    # Try to setup using imageio_ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_source = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Create a local bin directory
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        local_bin = project_root / 'bin'
        local_bin.mkdir(exist_ok=True)
        
        ffmpeg_dest = local_bin / 'ffmpeg.exe'
        
        # Copy FFmpeg to local bin if not already there
        if not ffmpeg_dest.exists():
            shutil.copy2(ffmpeg_source, ffmpeg_dest)
            print(f"✓ Copied FFmpeg to {ffmpeg_dest}")
        
        # Test it
        result = subprocess.run([str(ffmpeg_dest), '-version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg setup complete!")
            return str(ffmpeg_dest), str(local_bin)
        
    except Exception as e:
        print(f"❌ FFmpeg setup error: {e}")
        return None, None
    
    print("❌ FFmpeg not available")
    return None, None


def download_segment(ffmpeg_dir, url, start_time_str, end_time_str, extension, output_path, final_path):
    """Download a segment from YouTube video."""
    print("\n" + "=" * 70)
    print("Step 1: Downloading YouTube Video Segment")
    print("=" * 70)
    
    start_time = timestamp_to_seconds(start_time_str)
    end_time = timestamp_to_seconds(end_time_str)
    
    # Validate timestamp order
    if end_time <= start_time:
        print(f"\n❌ ERROR: END_TIME ({end_time_str} = {end_time}s) must be after START_TIME ({start_time_str} = {start_time}s)")
        return False
    
    duration = end_time - start_time
    path = final_path if extension == 'mp4' else output_path
    
    
    
    print(f"URL: {url}")
    print(f"Segment: {start_time_str} to {end_time_str} ({duration} seconds)")
    print(f"Output: {path}\n")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Add FFmpeg to PATH
    env = os.environ.copy()
    env['PATH'] = ffmpeg_dir + os.pathsep + env.get('PATH', '')
    
    # Download command - choose format based on extension
    if extension == 'mp4':
        # For MP4: Use more flexible format selection to work with YouTube SABR streaming
        # This allows any video + audio that can be merged to MP4
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            url,
            '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            '--merge-output-format', 'mp4',
            '--download-sections', f'*{start_time}-{end_time}',
            '-o', path,
            '--no-playlist',
        ]
    else:
        # For WebM: Use WebM-specific formats
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            url,
            '-f', 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]',
            '--merge-output-format', 'webm',
            '--download-sections', f'*{start_time}-{end_time}',
            '-o', path,
            '--no-playlist',
        ]
    
    print("Starting download...\n")
    print("-" * 70)
    
    try:
        timeout = max(300, duration * 2)
        result = subprocess.run(cmd, env=env, timeout=timeout)
        
        print("-" * 70)
        
        if result.returncode != 0:
            print(f"\n❌ Download failed (exit code {result.returncode})")
            return False
        
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024*1024)
            print(f"✅ Download successful!")
            print(f"   File: {os.path.abspath(path)}")
            print(f"   Size: {size_mb:.2f} MB\n")
            return True
        
        print("❌ File not created")
        return False
        
    except subprocess.TimeoutExpired:
        print("❌ Download timeout")
        return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False


def encode_video(ffmpeg_path, input_path, output_path, codec='h264', quality='lossless'):
    """Encode video to high-quality MP4."""
    print("\n" + "=" * 70)
    print("Step 2: Encoding to High-Quality MP4")
    print("=" * 70)
    
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Codec: {codec}, Quality: {quality}\n")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Codec configurations - using best lossless quality
    codec_settings = {
        'h264': {
            'lossless': ['-c:v', 'libx264', '-crf', '18', '-preset', 'slow'],
            'high': ['-c:v', 'libx264', '-crf', '23', '-preset', 'medium'],
        },
        'h265': {
            'lossless': ['-c:v', 'libx265', '-crf', '20', '-preset', 'slow'],
            'high': ['-c:v', 'libx265', '-crf', '25', '-preset', 'medium'],
        },
    }
    
    # Build encoding command
    cmd = [
        ffmpeg_path,
        '-i', input_path,
    ] + codec_settings[codec][quality] + [
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ar', '48000',
        '-movflags', '+faststart',
        '-pix_fmt', 'yuv420p',
        '-y',
        output_path
    ]
    
    print("Encoding... (this may take a few minutes)\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        if result.returncode != 0:
            print(f"❌ Encoding failed: {result.stderr[:300]}\n")
            return False
        
        if not os.path.exists(output_path):
            print("❌ Output file not created\n")
            return False
        
        output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        input_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        
        print(f"✅ Encoding successful!")
        print(f"   Input size:  {input_size_mb:.2f} MB")
        print(f"   Output size: {output_size_mb:.2f} MB")
        if input_size_mb > 0:
            compression = ((1 - output_size_mb/input_size_mb) * 100)
            print(f"   Compression: {compression:.1f}%")
        print(f"   Output: {os.path.abspath(output_path)}\n")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Encoding timeout\n")
        return False
    except Exception as e:
        print(f"❌ Encoding error: {e}\n")
        return False


def main():
    """Main function to download and encode YouTube video segment."""
    print("\n" + "=" * 70)
    print("YOUTUBE VIDEO DOWNLOADER & ENCODER")
    print("=" * 70 + "\n")
    
    # Configuration - MODIFY THESE VALUES
    VIDEO_URL = "https://www.youtube.com/watch?v=5135omtMu40"
    START_TIME = "1:08:57"  # hr:min:sec format
    END_TIME = "1:10:27"
    # EXTENSION = 'mp4'
    EXTENSION = ''
    # Optional: Change codec ('h264' or 'h265') and quality ('lossless' or 'high')
    CODEC = 'h264'
    QUALITY = 'lossless'
    
    # Setup paths
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"
    
    timestamp = int(datetime.now().timestamp())
    temp_file = input_dir / f"segment_{timestamp}.webm"
    final_file = output_dir / f"segment_{timestamp}.mp4"
    
    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Setup FFmpeg
    ffmpeg_path, ffmpeg_dir = setup_ffmpeg()
    if not ffmpeg_path or not ffmpeg_dir:
        print("\n❌ FFmpeg setup failed. Cannot proceed.")
        print("\nPlease install imageio-ffmpeg:")
        print("  pip install imageio-ffmpeg\n")
        return 1
    
    try:
        # Step 1: Download segment
        if not download_segment(ffmpeg_dir, VIDEO_URL, START_TIME, END_TIME, EXTENSION, str(temp_file), str(final_file)):
            print("\n❌ Download failed. Exiting.\n")
            return 1
        if not EXTENSION == 'mp4':
            if not encode_video(ffmpeg_path, str(temp_file), str(final_file), CODEC, QUALITY):
                print("\n❌ Encoding failed. Exiting.\n")
                return 1
        
        # Success!
        print("\n" + "=" * 70)
        print("✅ SUCCESS - Process Complete!")
        print("=" * 70)
        
        if EXTENSION == 'mp4':
            print(f"\n📁 Downloaded video: {final_file.absolute()}")
            print(f"   (Direct MP4 download, no encoding needed)\n")
        else:
            print(f"\n📁 Downloaded segment: {temp_file.absolute()}")
            print(f"📁 Encoded video:      {final_file.absolute()}\n")
            
            # Optional: Clean up intermediate file (only for webm)
            cleanup = input("\nDelete intermediate .webm file? (y/n): ").strip().lower()
            if cleanup == 'y':
                try:
                    os.remove(temp_file)
                    print(f"✅ Deleted {temp_file.name}\n")
                except Exception as e:
                    print(f"⚠️  Could not delete file: {e}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
