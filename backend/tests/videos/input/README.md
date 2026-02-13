# Test Video Input Directory

Place test video files here for encoding tests.

## Supported Formats
- MP4, AVI, MKV, MOV, FLV, WMV, WEBM, M4V, MPG, MPEG, 3GP

## Usage

1. Add your test video to this directory:
   ```
   tests/videos/input/my_test_video.avi
   ```

2. Run the encoding test:
   ```bash
   python tests/test_encoding.py
   ```

3. Find the encoded output in `tests/videos/output/`

## Getting a Test Video

If you don't have a test video, you can:

1. Download a short clip from YouTube:
   ```bash
   yt-dlp "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f "18" --download-sections "*0-10" -o "tests/videos/input/sample.mp4"
   ```

2. Or copy any video file from your computer to this directory
