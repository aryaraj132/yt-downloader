# Test Suite for YT-Downloader

## Directory Structure

```
tests/
├── videos/
│   ├── input/     # Place test video files here
│   └── output/    # Encoded videos will be saved here
├── test_encoding.py  # Video encoding service tests
└── test_download.py  # YouTube download tests
```

## Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup FFmpeg**:
   ```bash
   python setup_ffmpeg.py
   ```

## Running Tests

### Encoding Test

The encoding test will automatically find video files in `tests/videos/input/` and encode them to `tests/videos/output/`.

**Supported input formats**: MP4, AVI, MKV, MOV, FLV, WMV, WEBM, M4V, MPG, MPEG, 3GP

**Steps**:

1. **Add a test video** to `tests/videos/input/`
   - Any video format is supported
   - Example: `tests/videos/input/sample.avi`

2. **Run the test**:
   ```bash
   python tests/test_encoding.py
   ```

3. **Check output** in `tests/videos/output/`
   - Encoded file will be named: `{original_name}_{codec}_{quality}.mp4`
   - Example: `sample_h264_high.mp4`

**What the test does**:
- ✅ Verifies FFmpeg is installed and working
- ✅ Tests codec configurations (H.264, H.265, AV1)
- ✅ Validates video files
- ✅ Extracts video metadata (duration, resolution, codecs)
- ✅ Encodes video to MP4 with H.264 codec (default)
- ✅ Displays compression ratio and file sizes

**Testing other codecs**:

Edit `tests/test_encoding.py` and uncomment these lines to test H.265 or AV1:

```python
# Line ~169
test_video_encoding(test_video, codec='h265', quality='high')
test_video_encoding(test_video, codec='av1', quality='medium')  # AV1 is slow!
```

### Download Test

Tests YouTube video segment downloading:

```bash
python tests/test_download.py
```

This test downloads a specific time segment from a YouTube video.

## Quick Test with Sample Video

If you don't have a test video, you can:

1. **Download a small sample**:
   ```bash
   # Using yt-dlp to get a short clip
   yt-dlp "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f "18" --download-sections "*0-10" -o "tests/videos/input/sample.mp4"
   ```

2. **Or use any video file** you have on your computer

## Expected Output

When you run `python tests/test_encoding.py`, you should see:

```
======================================================================
VIDEO ENCODING SERVICE - TEST SUITE
======================================================================

======================================================================
Testing FFmpeg Availability
======================================================================
✅ FFmpeg found at: D:\yt-downloader\bin\ffmpeg.exe
   ffmpeg version N-xxxxx-gxxxxxx

✅ FFmpeg is working correctly

======================================================================
Testing Codec Configurations
======================================================================
✓ Codec h264 found
  ✓ Preset lossless configured
  ✓ Preset high configured
  ✓ Preset medium configured
...

======================================================================
Searching for Input Videos
======================================================================
Input directory: D:\yt-downloader\tests\videos\input

✅ Found 1 video file(s):
  - sample.avi (45.23 MB)

======================================================================
Testing Video Encoding: H264 (high)
======================================================================
Input: sample.avi
Validating video file...
✓ Video file is valid
Extracting metadata...
  Duration: 120.5 seconds
  Resolution: 1920x1080
  Video Codec: mpeg4
  Audio Codec: mp3

Encoding to: sample_h264_high.mp4
Codec: h264, Quality: high
This may take a few moments...

✅ Encoding successful!
   Input size:  45.23 MB
   Output size: 38.51 MB
   Compression: 14.9%
   Output: D:\yt-downloader\tests\videos\output\sample_h264_high.mp4

======================================================================
✅ ALL TESTS PASSED
======================================================================
```

## Troubleshooting

**"No module named 'dotenv'"**
```bash
pip install -r requirements.txt
```

**"FFmpeg not found"**
```bash
python setup_ffmpeg.py
```

**"No video files found"**
- Add a video file to `tests/videos/input/`
- Supported formats: MP4, AVI, MKV, MOV, FLV, WMV, WEBM, M4V, MPG, MPEG, 3GP

**Encoding is very slow**
- AV1 codec is significantly slower than H.264/H.265
- Large or high-resolution videos take longer
- This is normal behavior for video encoding
