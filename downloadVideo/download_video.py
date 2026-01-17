"""
Combined YouTube Video Downloader and Encoder
Downloads a segment of a YouTube video and encodes it to high-quality MP4.

This version uses shared services for all encoding/download operations.
"""
import os
import sys
import re
import time
from pathlib import Path
from datetime import datetime

# Add src to path to import services
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.services import ffmpeg_utils_service
from src.services.encoding_service import EncodingService


def select_input_file(input_dir):
    """
    List all video files in the input directory and prompt user to select one.
    Returns the selected file path or None if no files found or invalid selection.
    """
    video_extensions = {'.webm', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.m4v'}
    video_files = []
    
    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            video_files.append(file_path)
    
    if not video_files:
        print(f"❌ No video files found in {input_dir}")
        return None
    
    # Sort by modification time (newest first)
    video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print("\n" + "=" * 70)
    print("Available video files in input folder:")
    print("=" * 70)
    
    for idx, file_path in enumerate(video_files, 1):
        size_mb = file_path.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        print(f"{idx}. {file_path.name}")
        print(f"   Size: {size_mb:.2f} MB | Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    while True:
        selection = input(f"\nSelect a file to encode (1-{len(video_files)}) or 'q' to quit: ").strip()
        
        if selection.lower() == 'q':
            return None
        
        try:
            file_idx = int(selection) - 1
            
            if 0 <= file_idx < len(video_files):
                selected_file = video_files[file_idx]
                print(f"\n✅ Selected: {selected_file.name}\n")
                return selected_file
            else:
                print(f"❌ Invalid selection. Please enter a number between 1 and {len(video_files)}.")
        
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.\n")
            return None


def download_segment(url, start_time_str, end_time_str, extension, output_path, final_path):
    """Download a segment from YouTube video using VideoService."""
    print("\n" + "=" * 70)
    print("Step 1: Downloading YouTube Video Segment")
    print("=" * 70)
    
    start_time = ffmpeg_utils_service.timestamp_to_seconds(start_time_str)
    end_time = ffmpeg_utils_service.timestamp_to_seconds(end_time_str)
    
    # Validate timestamp order
    if end_time <= start_time:
        print(f"\n❌ ERROR: END_TIME ({end_time_str} = {end_time}s) must be after START_TIME ({start_time_str} = {start_time}s)")
        return False
    
    duration = end_time - start_time
    path = final_path if extension == 'mp4' else output_path
    
    print(f"URL: {url}")
    print(f"Segment: {start_time_str} to {end_time_str} ({duration} seconds)")
    print(f"Output: {path}\n")
    
    # Progress callback for console display
    last_update = [0]
    def progress_callback(data):
        import time
        now = time.time()
        if now - last_update[0] >= 0.3:
            last_update[0] = now
            
            if 'phase' in data and data['phase'] == 'Merging':
                print()  # New line before merge message
                print("Merging video and audio streams...")
            elif 'percent' in data:
                percent = data['percent']
                size = data.get('size', '?')
                speed = data.get('speed', '?')
                eta = data.get('eta', '?')
                
                # Progress bar
                bar_width = 40
                filled = int(bar_width * percent / 100)
                bar = '█' * filled + '░' * (bar_width - filled)
                print(f"\r[{bar}] {percent:.1f}% of {size} | {speed} | ETA: {eta}", end='', flush=True)
    
    print("Downloading...\n")
    
    # Use VideoService - no database needed
    from src.services.video_service import VideoService
    success, file_path, error = VideoService.download_video_segment(
        url=url,
        start_time=start_time,
        end_time=end_time,
        output_path=str(path),
        format_preference=extension if extension else 'webm',
        resolution_preference='best',
        video_id=None,  # No database tracking
        progress_callback=progress_callback
    )
    
    print()  # New line after progress
    
    if success:
        size_mb = os.path.getsize(path) / (1024*1024)
        print(f"\n✅ Download successful!")
        print(f"   File: {os.path.abspath(path)}")
        print(f"   Size: {size_mb:.2f} MB\n")
        return True
    else:
        print(f"\n❌ Download failed: {error}\n")
        return False


def encode_video_with_progress(ffmpeg_path, input_path, output_path, codec='h264', quality='lossless'):
    """Encode video using EncodingService with console progress display."""
    
    print("\n" + "=" * 70)
    print("Step 2: Encoding to High-Quality MP4")
    print("=" * 70)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Codec: {codec}, Quality: {quality}")
    
    # Get duration for progress tracking
    duration = ffmpeg_utils_service.get_video_duration(ffmpeg_path, input_path)
    
    if duration:
        print(f"Duration: {int(duration//60)}:{int(duration%60):02d}")
    else:
        print(f"Duration: Unknown (will show alternative progress indicators)")
    
    # Detect GPU
    gpu_encoder, gpu_type = ffmpeg_utils_service.detect_gpu_encoder(ffmpeg_path, codec)
    if gpu_encoder:
        print(f"🚀 GPU Acceleration: {gpu_type} ({gpu_encoder})")
    else:
        print(f"💻 Using CPU encoder")
    
    print("\nEncoding in progress...\n")
    
    # Progress tracking variables
    last_update = [0]  # Use list for mutable closure
    start_time = time.time()
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spinner_idx = [0]
    
    def progress_callback(data):
        """Display progress to console."""
        nonlocal last_update, spinner_idx
        
        now = time.time()
        if now - last_update[0] < 0.5:  # Throttle display updates
            return
        last_update[0] = now
        
        if 'percent' in data and duration:
            # Progress bar mode
            percent = data.get('percent', 0)
            eta = data.get('eta', '??:??')
            speed = data.get('speed', '?x')
            
            bar_width = 40
            filled = int(bar_width * percent / 100)
            bar = '█' * filled + '░' * (bar_width - filled)
            
            print(f"\r[{bar}] {percent:.1f}% | ETA: {eta} | Speed: {speed}", end='', flush=True)
        else:
            # Fallback mode (no duration)
            current_time = data.get('current_time', 0)
            frame = data.get('frame', 0)
            fps = data.get('fps', 0)
            speed = data.get('speed', '?x')
            elapsed = int(now - start_time)
            
            spinner = spinner_chars[spinner_idx[0] % len(spinner_chars)]
            spinner_idx[0] += 1
            
            # Format current time
            hours = int(current_time // 3600)
            minutes = int((current_time % 3600) // 60)
            seconds = int(current_time % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            print(f"\r{spinner} Encoding: {time_str} | Frame: {frame} | FPS: {fps:.1f} | Speed: {speed} | Elapsed: {elapsed//60:02d}:{elapsed%60:02d}", 
                  end='', flush=True)
    
    try:
        # Use EncodingService to encode
        success, error = EncodingService.encode_video_to_mp4(
            input_path,
            output_path,
            video_codec=codec,
            quality_preset=quality,
            use_gpu=True,
            encode_id=None,
            progress_callback=progress_callback
        )
        
        print()  # New line after progress
        
        if success:
            size_mb = os.path.getsize(output_path) / (1024*1024)
            print(f"\n✅ Encoding successful!")
            print(f"   Output: {os.path.abspath(output_path)}")
            print(f"   Size: {size_mb:.2f} MB\n")
            return True
        else:
            print(f"\n❌ Encoding failed: {error}\n")
            return False
            
    except Exception as e:
        print(f"\n❌ Encoding error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to download and encode YouTube video segment."""
    print("\n" + "=" * 70)
    print("YOUTUBE VIDEO DOWNLOADER & ENCODER")
    print("=" * 70 + "\n")
    
    # Configuration - MODIFY THESE VALUES
    VIDEO_URL = "https://www.youtube.com/watch?v=fRdMGjcqczM"
    START_TIME = "1:14:44"  # hr:min:sec format
    END_TIME = "3:12:21"
    # EXTENSION = 'mp4'
    EXTENSION = ''
    
    # Codec options: 'h264', 'h265', or 'av1'
    # - h264: Fast, universal compatibility (recommended for most use cases)
    # - h265: Better compression than h264, slower encoding
    # - av1: Best compression (30-50% smaller), slowest encoding, requires newer hardware for playback
    CODEC = 'h264'
    
    # Quality options: 'lossless' or 'high'
    QUALITY = 'lossless'
    
    # Set to True to only encode an existing file (skips download)
    ONLY_ENCODE = True
    
    # Setup paths
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"
    
    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Determine file paths
    if ONLY_ENCODE:
        # Interactive file selection
        temp_file = select_input_file(input_dir)
        if not temp_file:
            print("\n❌ No file selected or no files available. Exiting.\n")
            return 1
        
        # Generate output filename based on input
        final_file = output_dir / f"{temp_file.stem}_encoded.mp4"
    else:
        # Timestamped filenames for new downloads
        timestamp = int(datetime.now().timestamp())
        temp_file = input_dir / f"segment_{timestamp}.webm"
        final_file = output_dir / f"segment_{timestamp}.mp4"
    
    # Setup FFmpeg
    print("\n" + "=" * 70)
    print("Setting up FFmpeg...")
    print("=" * 70)
    
    ffmpeg_path, ffmpeg_dir = ffmpeg_utils_service.setup_ffmpeg()
    
    if not ffmpeg_path or not ffmpeg_dir:
        print("\n❌ FFmpeg not available. Exiting.\n")
        return 1
    
    # Execute workflow
    try:
        # Step 1: Download (if needed)
        if not ONLY_ENCODE:
            success = download_segment(
                VIDEO_URL,
                START_TIME,
                END_TIME,
                EXTENSION,
                str(temp_file),
                str(final_file)
            )
            
            if not success:
                print("\n❌ Download failed. Exiting.\n")
                return 1
        
        # Step 2: Encode (if needed)
        if EXTENSION != 'mp4':
            if not os.path.exists(temp_file):
                print(f"\n❌ Input file not found: {temp_file}")
                print("   Hint: Set ONLY_ENCODE = False to download first\n")
                return 1
            
            success = encode_video_with_progress(
                str(temp_file),
                str(final_file),
                CODEC,
                QUALITY
            )
            
            if not success:
                print("\n❌ Encoding failed. Exiting.\n")
                return 1
        
        # Success!
        print("\n" + "=" * 70)
        if EXTENSION == 'mp4':
            print("✅ SUCCESS! Video downloaded directly as MP4.")
        elif ONLY_ENCODE:
            print("✅ SUCCESS! Video encoded to MP4.")
        else:
            print("✅ SUCCESS! Video downloaded and encoded to MP4.")
        print("=" * 70)
        print(f"Final file: {final_file.absolute()}\n")
        
        # Cleanup intermediate file if not in ONLY_ENCODE mode
        if not ONLY_ENCODE and temp_file.exists() and temp_file != final_file:
            print(f"Cleaning up intermediate file: {temp_file.name}")
            try:
                temp_file.unlink()
                print("✓ Cleanup complete\n")
            except Exception as e:
                print(f"⚠️  Could not delete intermediate file: {e}\n")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.\n")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
