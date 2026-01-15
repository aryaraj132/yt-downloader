"""
Standalone test script for video encoding service.
This version doesn't require full app configuration.
"""
import os
import sys
from pathlib import Path
import subprocess
import json
import re

# Test directories
SCRIPT_DIR = Path(__file__).parent
INPUT_DIR = SCRIPT_DIR / "videos" / "input"
OUTPUT_DIR = SCRIPT_DIR / "videos" / "output"


def get_ffmpeg_path():
    """Get FFmpeg binary location."""
    project_root = SCRIPT_DIR.parent
    bin_dir = project_root / 'bin'
    ffmpeg_path = bin_dir / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    
    if ffmpeg_path.exists():
        return str(ffmpeg_path)
    
    # Fall back to imageio-ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def test_ffmpeg_availability():
    """Test if FFmpeg is available."""
    print("=" * 70)
    print("Testing FFmpeg Availability")
    print("=" * 70)
    
    ffmpeg_path = get_ffmpeg_path()
    
    if ffmpeg_path:
        print(f"✅ FFmpeg found at: {ffmpeg_path}")
        
        try:
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"   {version_line}")
                print("\n✅ FFmpeg is working correctly\n")
                return ffmpeg_path
            else:
                print("\n⚠️  FFmpeg found but not working\n")
                return None
        except Exception as e:
            print(f"\n⚠️  FFmpeg test failed: {str(e)}\n")
            return None
    else:
        print("❌ FFmpeg not found")
        print("   Run: python setup_ffmpeg.py")
        print("   Or install imageio-ffmpeg: pip install imageio-ffmpeg\n")
        return None


def find_input_videos():
    """Find video files in input directory."""
    print("=" * 70)
    print("Searching for Input Videos")
    print("=" * 70)
    
    print(f"Input directory: {INPUT_DIR.absolute()}")
    
    # Ensure directories exist
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Supported video formats
    video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.flv', 
                       '*.wmv', '*.webm', '*.m4v', '*.mpg', '*.mpeg', '*.3gp']
    
    video_files = []
    for ext in video_extensions:
        video_files.extend(INPUT_DIR.glob(ext))
    
    if video_files:
        print(f"\n✅ Found {len(video_files)} video file(s):")
        for vf in video_files:
            size_mb = vf.stat().st_size / (1024 * 1024)
            print(f"  - {vf.name} ({size_mb:.2f} MB)")
        print()
    else:
        print("\n⚠️  No video files found in input directory")
        print(f"   Please add a test video to: {INPUT_DIR.absolute()}")
        print(f"   Supported formats: {', '.join([e.replace('*.', '') for e in video_extensions])}\n")
    
    return video_files


def get_video_metadata(ffmpeg_path, video_path):
    """Extract video metadata using ffprobe."""
    try:
        ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
        
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration,size:stream=codec_name,codec_type,width,height',
            '-of', 'json',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        metadata = {
            'duration': float(data.get('format', {}).get('duration', 0)),
            'size_bytes': int(data.get('format', {}).get('size', 0)),
        }
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                metadata['video_codec'] = stream.get('codec_name')
                metadata['width'] = stream.get('width')
                metadata['height'] = stream.get('height')
            elif stream.get('codec_type') == 'audio':
                metadata['audio_codec'] = stream.get('codec_name')
        
        return metadata
    except Exception as e:
        print(f"⚠️  Metadata extraction failed: {str(e)}")
        return None


def encode_video(ffmpeg_path, input_path, output_path, codec='h264', quality='high'):
    """Encode video to MP4."""
    print("=" * 70)
    print(f"Testing Video Encoding: {codec.upper()} ({quality})")
    print("=" * 70)
    
    print(f"Input: {input_path.name}")
    
    # Get metadata
    print("Extracting metadata...")
    metadata = get_video_metadata(ffmpeg_path, input_path)
    
    if metadata:
        print(f"  Duration: {metadata.get('duration', 'N/A')} seconds")
        print(f"  Resolution: {metadata.get('width', '?')}x{metadata.get('height', '?')}")
        print(f"  Video Codec: {metadata.get('video_codec', 'N/A')}")
        print(f"  Audio Codec: {metadata.get('audio_codec', 'N/A')}")
    
    # Codec configurations
    codec_settings = {
        'h264': {
            'lossless': ['-c:v', 'libx264', '-crf', '18', '-preset', 'slow'],
            'high': ['-c:v', 'libx264', '-crf', '23', '-preset', 'medium'],
            'medium': ['-c:v', 'libx264', '-crf', '28', '-preset', 'fast']
        },
        'h265': {
            'lossless': ['-c:v', 'libx265', '-crf', '20', '-preset', 'slow'],
            'high': ['-c:v', 'libx265', '-crf', '25', '-preset', 'medium'],
            'medium': ['-c:v', 'libx265', '-crf', '30', '-preset', 'fast']
        },
        'av1': {
            'lossless': ['-c:v', 'libaom-av1', '-crf', '15', '-cpu-used', '4', '-row-mt', '1'],
            'high': ['-c:v', 'libaom-av1', '-crf', '30', '-cpu-used', '4', '-row-mt', '1'],
            'medium': ['-c:v', 'libaom-av1', '-crf', '35', '-cpu-used', '6', '-row-mt', '1']
        }
    }
    
    # Build command
    cmd = [
        ffmpeg_path,
        '-i', str(input_path),
    ] + codec_settings[codec][quality] + [
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ar', '48000',
        '-movflags', '+faststart',
        '-pix_fmt', 'yuv420p',
        '-y',
        str(output_path)
    ]
    
    print(f"\nEncoding to: {output_path.name}")
    print(f"Codec: {codec}, Quality: {quality}")
    print("This may take a few moments...\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        if result.returncode != 0:
            print(f"❌ Encoding failed: {result.stderr[:200]}\n")
            return False
        
        if not output_path.exists():
            print("❌ Output file not created\n")
            return False
        
        output_size_mb = output_path.stat().st_size / (1024 * 1024)
        input_size_mb = input_path.stat().st_size / (1024 * 1024)
        
        print(f"✅ Encoding successful!")
        print(f"   Input size:  {input_size_mb:.2f} MB")
        print(f"   Output size: {output_size_mb:.2f} MB")
        if input_size_mb > 0:
            print(f"   Compression: {((1 - output_size_mb/input_size_mb) * 100):.1f}%")
        print(f"   Output: {output_path.absolute()}\n")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Encoding timeout\n")
        return False
    except Exception as e:
        print(f"❌ Encoding error: {str(e)}\n")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("VIDEO ENCODING SERVICE - STANDALONE TEST")
    print("=" * 70 + "\n")
    
    try:
        # Test FFmpeg
        ffmpeg_path = test_ffmpeg_availability()
        if not ffmpeg_path:
            print("❌ Cannot proceed without FFmpeg\n")
            print("Setup instructions:")
            print("1. Run: python setup_ffmpeg.py")
            print("   OR")
            print("2. Install: pip install imageio-ffmpeg\n")
            return 1
        
        # Find input videos
        video_files = find_input_videos()
        
        if not video_files:
            print("=" * 70)
            print("⚠️  NO VIDEOS TO TEST")
            print("=" * 70)
            print("\nAdd a test video to continue:")
            print(f"  {INPUT_DIR.absolute()}\n")
            return 0
        
        # Test encoding with first video
        test_video = video_files[0]
        output_filename = f"{test_video.stem}_h264_high.mp4"
        output_path = OUTPUT_DIR / output_filename
        
        if not encode_video(ffmpeg_path, test_video, output_path, codec='h264', quality='high'):
            return 1
        
        print("=" * 70)
        print("✅ TEST PASSED")
        print("=" * 70 + "\n")
        
        print("Encoded video saved to:")
        print(f"  {output_path.absolute()}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
