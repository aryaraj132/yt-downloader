"""
Standalone test script for video encoding service.
Uses the shared EncodingService for all encoding operations.
"""
import os
import sys
from pathlib import Path

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.services import ffmpeg_utils_service
from src.services.encoding_service import EncodingService

# Test directories
INPUT_DIR = script_dir / "videos" / "input"
OUTPUT_DIR = script_dir / "videos" / "output"


def test_ffmpeg_availability():
    """Test if FFmpeg is available."""
    print("\n" + "=" * 70)
    print("FFmpeg Availability Test")
    print("=" * 70)
    
    ffmpeg_path, ffmpeg_dir = ffmpeg_utils_service.setup_ffmpeg()
    
    if not ffmpeg_path or not ffmpeg_dir:
        print("❌ FFmpeg not available")
        return False
    
    print(f"✅ FFmpeg path: {ffmpeg_path}")
    print(f"✅ FFmpeg directory: {ffmpeg_dir}")
    return True, ffmpeg_path


def find_input_videos():
    """Find video files in input directory."""
    print("\n" + "=" * 70)
    print("Finding Input Videos")
    print("=" * 70)
    
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    video_extensions = {'.webm', '.mp4', '.mkv', '.avi', '.mov', '.flv'}
    videos = []
    
    for file_path in INPUT_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            videos.append((file_path, size_mb))
    
    if not videos:
        print(f"⚠️  No video files found in {INPUT_DIR}")
        print("   Please place test video files in this directory")
        return []
    
    print(f"Found {len(videos)} video file(s):")
    for video_path, size_mb in videos:
        print(f"  • {video_path.name} ({size_mb:.2f} MB)")
    
    return videos


def test_gpu_detection(ffmpeg_path):
    """Test GPU encoder detection."""
    print("\n" + "=" * 70)
    print("GPU Detection Test")
    print("=" * 70)
    
    for codec in ['h264', 'h265', 'av1']:
        encoder, gpu_type = ffmpeg_utils_service.detect_gpu_encoder(ffmpeg_path, codec)
        if encoder:
            print(f"✅ {codec.upper()}: {gpu_type} ({encoder})")
        else:
            print(f"ℹ️  {codec.upper()}: No GPU encoder (will use CPU)")
    
    return True


def test_video_metadata(ffmpeg_path, video_path):
    """Test video metadata extraction."""
    print("\n" + "="  * 70)
    print(f"Video Metadata Test: {video_path.name}")
    print("=" * 70)
    
    # Test duration detection
    duration = ffmpeg_utils_service.get_video_duration(ffmpeg_path, str(video_path))
    if duration:
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        print(f"✅ Duration: {minutes}:{seconds:02d} ({duration:.2f}s)")
    else:
        print("⚠️  Could not determine duration")
    
    # Test full metadata
    metadata = EncodingService.get_video_metadata(str(video_path))
    if metadata:
        print("\nMetadata:")
        for key, value in metadata.items():
            print(f"  • {key}: {value}")
        return True
    else:
        print("❌ Could not get metadata")
        return False


def test_encoding(ffmpeg_path, video_path, codec='h264', quality='high'):
    """Test video encoding with progress display."""
    print("\n" + "=" * 70)
    print(f"Encoding Test: {codec.upper()} @ {quality}")
    print("=" * 70)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{video_path.stem}_encoded_{codec}_{quality}.mp4"
    
    print(f"Input:  {video_path}")
    print(f"Output: {output_path}")
    
    # Progress callback for console display
    import time
    last_update = [0]
    start_time = time.time()
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spinner_idx = [0]
    
    def progress_callback(data):
        now = time.time()
        if now - last_update[0] < 0.5:
            return
        last_update[0] = now
        
        if 'percent' in data:
            percent = data.get('percent', 0)
            eta = data.get('eta', '??:??')
            speed = data.get('speed', '?x')
            bar_width = 40
            filled = int(bar_width * percent / 100)
            bar = '█' * filled + '░' * (bar_width - filled)
            print(f"\r[{bar}] {percent:.1f}% | ETA: {eta} | Speed: {speed}", end='', flush=True)
        else:
            # Fallback progress
            frame = data.get('frame', 0)
            fps = data.get('fps', 0)
            speed = data.get('speed', '?x')
            elapsed = int(now - start_time)
            s = spinner[spinner_idx[0] % len(spinner)]
            spinner_idx[0] += 1
            print(f"\r{s} Frame: {frame} | FPS: {fps:.1f} | Speed: {speed} | Elapsed: {elapsed//60:02d}:{elapsed%60:02d}", 
                  end='', flush=True)
    
    # Encode using service
    success, error = EncodingService.encode_video_to_mp4(
        str(video_path),
        str(output_path),
        video_codec=codec,
        quality_preset=quality,
        use_gpu=True,
        encode_id=None,
        progress_callback=progress_callback
    )
    
    print()  # New line after progress
    
    if success:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Encoding successful!")
        print(f"   Output: {output_path}")
        print(f"   Size: {size_mb:.2f} MB")
        return True
    else:
        print(f"\n❌ Encoding failed: {error}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("VIDEO ENCODING SERVICE - TEST SUITE")
    print("=" * 70)
    
    # Test 1: FFmpeg Availability
    result = test_ffmpeg_availability()
    if not result:
        return 1
    success, ffmpeg_path = result
    
    # Test 2: GPU Detection
    if not test_gpu_detection(ffmpeg_path):
        print("\n⚠️  GPU detection test failed (non-critical)")
    
    # Test 3: Find videos
    videos = find_input_videos()
    if not videos:
        print("\n❌ No test videos found. Please add video files to:")
        print(f"   {INPUT_DIR}")
        return 1
    
    # Test 4: Metadata for first video
    video_path, _ = videos[0]
    if not test_video_metadata(ffmpeg_path, video_path):
        print("\n⚠️  Metadata test failed (non-critical)")
    
    # Test 5: Encoding
    print("\n" + "=" * 70)
    print("Starting Encoding Tests")
    print("=" * 70)
    print("\nNote: This will encode the first video found with different settings")
    print("      You can cancel with Ctrl+C\n")
    
    tests_to_run = [
        ('h264', 'high'),
        # Uncomment to test more codecs:
        # ('h265', 'high'),
        # ('av1', 'high'),
    ]
    
    passed = 0
    failed = 0
    
    for codec, quality in tests_to_run:
        try:
            if test_encoding(ffmpeg_path, video_path, codec, quality):
                passed += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            print("\n\n⚠️  Test cancelled by user")
            break
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" +"=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
