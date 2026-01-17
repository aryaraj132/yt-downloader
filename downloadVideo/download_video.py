"""
Combined YouTube Video Downloader and Encoder
Downloads a segment of a YouTube video and encodes it to high-quality MP4.
"""
import os
import sys
import subprocess
import shutil
import re
import time
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


def get_video_duration(ffmpeg_path, video_path):
    """
    Get the duration of a video file in seconds using ffprobe or ffmpeg.
    Returns None if duration cannot be determined.
    This should be very fast (under 1 second) as it only reads metadata.
    """
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
        cmd = [
            ffmpeg_path,
            '-i', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Duration is in stderr (ffmpeg outputs metadata to stderr)
        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', result.stderr)
        if duration_match:
            hours, minutes, seconds = duration_match.groups()
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            
        return None
        
    except subprocess.TimeoutExpired:
        print(f"⚠️  Video duration check timed out (this shouldn't happen - may indicate a corrupted file)")
        print(f"   Encoding will continue without progress bar\n")
        return None
    except Exception as e:
        print(f"⚠️  Could not determine video duration: {e}")
        print(f"   Encoding will continue without progress bar\n")
        return None


def detect_gpu_encoder(ffmpeg_path, codec='h264'):
    """
    Detect available GPU encoders for the given codec by actually testing them.
    Returns tuple: (encoder_name, encoder_type) or (None, None) if no GPU available.
    """
    encoders_to_test = []
    
    if codec == 'h264':
        # Test in order: AMD → NVIDIA → Intel (prioritize AMD for user's system)
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
                return encoder, gpu_type
        except Exception:
            # This encoder doesn't work, try next one
            continue
    
    return None, None


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


def encode_video(ffmpeg_path, input_path, output_path, codec='h264', quality='lossless', use_gpu=True, duration=None):
    """Encode video to high-quality MP4 with GPU acceleration and progress tracking."""
    print("\n" + "=" * 70)
    print("Step 2: Encoding to High-Quality MP4")
    print("=" * 70)
    
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Codec: {codec}, Quality: {quality}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Get video duration for progress tracking (only if not already provided)
    if duration is None:
        duration = get_video_duration(ffmpeg_path, input_path)
    
    if duration:
        print(f"Duration: {int(duration//3600):02d}:{int((duration%3600)//60):02d}:{int(duration%60):02d}")
    else:
        print("Duration: Unknown (will show alternative progress indicators)")
    
    # Detect GPU encoder if requested
    gpu_encoder = None
    gpu_type = None
    if use_gpu:
        gpu_encoder, gpu_type = detect_gpu_encoder(ffmpeg_path, codec)
        if gpu_encoder:
            print(f"🚀 GPU Acceleration: {gpu_type} ({gpu_encoder})")
        else:
            print("ℹ️  No GPU encoder detected, using CPU")
    else:
        print("ℹ️  GPU disabled, using CPU")
    
    print()
    
    # Build encoding command based on encoder type
    if gpu_encoder:
        # GPU encoding settings
        if 'nvenc' in gpu_encoder:
            # NVIDIA settings
            if quality == 'lossless':
                video_settings = ['-c:v', gpu_encoder, '-preset', 'p7', '-cq', '19', '-b:v', '0']
            else:
                video_settings = ['-c:v', gpu_encoder, '-preset', 'p5', '-cq', '23', '-b:v', '0']
        elif 'amf' in gpu_encoder:
            # AMD settings
            if quality == 'lossless':
                video_settings = ['-c:v', gpu_encoder, '-quality', 'quality', '-qp_i', '18', '-qp_p', '18']
            else:
                video_settings = ['-c:v', gpu_encoder, '-quality', 'balanced', '-qp_i', '23', '-qp_p', '23']
        elif 'qsv' in gpu_encoder:
            # Intel QuickSync settings
            if quality == 'lossless':
                video_settings = ['-c:v', gpu_encoder, '-preset', 'veryslow', '-global_quality', '18']
            else:
                video_settings = ['-c:v', gpu_encoder, '-preset', 'medium', '-global_quality', '23']
        else:
            # Fallback to CPU
            gpu_encoder = None
    
    if not gpu_encoder:
        # CPU encoding settings
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
        video_settings = codec_settings[codec][quality]
    
    # Build complete FFmpeg command
    cmd = [
        ffmpeg_path,
        '-i', input_path,
        '-progress', 'pipe:2',  # Output progress to stderr
    ] + video_settings + [
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ar', '48000',
        '-movflags', '+faststart',
        '-pix_fmt', 'yuv420p',
        '-y',
        output_path
    ]
    
    print("Encoding in progress...\n")
    
    try:
        # Run FFmpeg with real-time progress monitoring
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        start_time = time.time()
        last_update = 0
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        spinner_idx = 0
        
        # Parse progress from stderr
        for line in process.stderr:
            # Look for time progress (format: time=00:01:23.45)
            time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
            
            if time_match and duration:
                # Progress bar mode (when duration is known)
                hours, minutes, seconds = time_match.groups()
                current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                
                # Update progress display (throttle to once per 0.5 seconds)
                now = time.time()
                if now - last_update >= 0.5:
                    last_update = now
                    
                    progress_pct = (current_time / duration) * 100
                    elapsed = now - start_time
                    
                    # Calculate ETA
                    if current_time > 0:
                        estimated_total = (elapsed / current_time) * duration
                        eta_seconds = estimated_total - elapsed
                        eta_str = f"{int(eta_seconds//60):02d}:{int(eta_seconds%60):02d}"
                    else:
                        eta_str = "calculating..."
                    
                    # Speed multiplier
                    speed_match = re.search(r'speed=\s*([\d.]+)x', line)
                    speed = speed_match.group(1) if speed_match else "?"
                    
                    # Display progress bar
                    bar_width = 40
                    filled = int(bar_width * progress_pct / 100)
                    bar = '█' * filled + '░' * (bar_width - filled)
                    
                    print(f"\r[{bar}] {progress_pct:.1f}% | ETA: {eta_str} | Speed: {speed}x", end='', flush=True)
            
            elif time_match:
                # Fallback mode (when duration is unknown)
                now = time.time()
                if now - last_update >= 0.5:
                    last_update = now
                    
                    hours, minutes, seconds = time_match.groups()
                    current_time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(float(seconds)):02d}"
                    elapsed = now - start_time
                    elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
                    
                    # Get frame count and fps
                    frame_match = re.search(r'frame=\s*(\d+)', line)
                    fps_match = re.search(r'fps=\s*([\d.]+)', line)
                    speed_match = re.search(r'speed=\s*([\d.]+)x', line)
                    
                    frame = frame_match.group(1) if frame_match else "?"
                    fps = fps_match.group(1) if fps_match else "?"
                    speed = speed_match.group(1) if speed_match else "?"
                    
                    # Spinner animation
                    spinner = spinner_chars[spinner_idx % len(spinner_chars)]
                    spinner_idx += 1
                    
                    print(f"\r{spinner} Encoding: {current_time_str} | Frame: {frame} | FPS: {fps} | Speed: {speed}x | Elapsed: {elapsed_str}", end='', flush=True)
        
        # Wait for process to complete
        process.wait()
        print()  # New line after progress display
        
        if process.returncode != 0:
            # If GPU encoding failed, retry with CPU (pass duration to avoid re-checking)
            if gpu_encoder:
                print(f"\n⚠️  GPU encoding failed, retrying with CPU...\n")
                return encode_video(ffmpeg_path, input_path, output_path, codec, quality, use_gpu=False, duration=duration)
            else:
                print(f"\n❌ Encoding failed (exit code {process.returncode})\n")
                return False
        
        if not os.path.exists(output_path):
            print("❌ Output file not created\n")
            return False
        
        # Success!
        elapsed_time = time.time() - start_time
        output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        input_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        
        print(f"\n✅ Encoding successful!")
        print(f"   Encoding time: {int(elapsed_time//60)}m {int(elapsed_time%60)}s")
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
        import traceback
        traceback.print_exc()
        return False


def select_input_file(input_dir):
    """
    List all video files in the input directory and prompt user to select one.
    Returns the selected file path or None if no files found or invalid selection.
    """
    # Common video file extensions
    video_extensions = {'.webm', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.m4v'}
    
    # Get all video files in input directory
    video_files = []
    if input_dir.exists():
        for file_path in input_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                video_files.append(file_path)
    
    if not video_files:
        print(f"\n❌ No video files found in: {input_dir.absolute()}")
        print("   Please download a video first before using ONLY_ENCODE mode.\n")
        return None
    
    # Sort files by modification time (newest first)
    video_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Display available files
    print("\n" + "=" * 70)
    print("Available video files in input folder:")
    print("=" * 70)
    
    for idx, file_path in enumerate(video_files, 1):
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{idx}. {file_path.name}")
        print(f"   Size: {file_size_mb:.2f} MB | Modified: {mod_time}")
    
    print("=" * 70)
    
    # Prompt user to select
    while True:
        try:
            selection = input(f"\nSelect a file to encode (1-{len(video_files)}) or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                print("Cancelled by user.\n")
                return None
            
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
    # Optional: Change codec ('h264' or 'h265') and quality ('lossless' or 'high')
    CODEC = 'h264'
    QUALITY = 'lossless'
    ONLY_ENCODE = True
    
    # Setup paths
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"
    
    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # When ONLY_ENCODE is True, prompt user to select an existing file
    # When False, use timestamps to avoid overwriting previous downloads
    if ONLY_ENCODE:
        selected_file = select_input_file(input_dir)
        if selected_file is None:
            return 1  # Exit if no file selected or found
        
        temp_file = selected_file
        # Generate output filename based on input file
        output_filename = f"{selected_file.stem}_encoded.mp4"
        final_file = output_dir / output_filename
    else:
        timestamp = int(datetime.now().timestamp())
        temp_file = input_dir / f"segment_{timestamp}.webm"
        final_file = output_dir / f"segment_{timestamp}.mp4"

    
    # Setup FFmpeg
    ffmpeg_path, ffmpeg_dir = setup_ffmpeg()
    if not ffmpeg_path or not ffmpeg_dir:
        print("\n❌ FFmpeg setup failed. Cannot proceed.")
        print("\nPlease install imageio-ffmpeg:")
        print("  pip install imageio-ffmpeg\n")
        return 1
    
    try:
        # Step 1: Download segment
        if not ONLY_ENCODE:
            if not download_segment(ffmpeg_dir, VIDEO_URL, START_TIME, END_TIME, EXTENSION, str(temp_file), str(final_file)):
                print("\n❌ Download failed. Exiting.\n")
                return 1
        
        # Step 2: Encode if needed (either ONLY_ENCODE mode or downloaded non-mp4)
        # Only encode if: (1) We're in ONLY_ENCODE mode OR (2) Downloaded format is not mp4
        # AND the input file exists
        if (ONLY_ENCODE or EXTENSION != 'mp4'):
            # Check if the input file exists before encoding
            if not os.path.exists(temp_file):
                print(f"\n❌ Input file not found: {temp_file}")
                print("   Make sure the file exists before using ONLY_ENCODE mode.\n")
                return 1
            
            if not encode_video(ffmpeg_path, str(temp_file), str(final_file), CODEC, QUALITY):
                print("\n❌ Encoding failed. Exiting.\n")
                return 1
        
        # Success!
        print("\n" + "=" * 70)
        print("✅ SUCCESS - Process Complete!")
        print("=" * 70)
        
        if ONLY_ENCODE:
            print(f"\n📁 Input file:    {temp_file.absolute()}")
            print(f"📁 Encoded video: {final_file.absolute()}")
            print("   (Encoding only mode - download was skipped)\n")
        elif EXTENSION == 'mp4':
            print(f"\n📁 Downloaded video: {final_file.absolute()}")
            print(f"   (Direct MP4 download, no encoding needed)\n")
        else:
            print(f"\n📁 Downloaded segment: {temp_file.absolute()}")
            print(f"📁 Encoded video:      {final_file.absolute()}\n")
            
            # Optional: Clean up intermediate file (only for webm downloads, not ONLY_ENCODE mode)
            # cleanup = input("\nDelete intermediate .webm file? (y/n): ").strip().lower()
            # if cleanup == 'y':
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
