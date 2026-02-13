# YouTube Video Downloader & Encoder

This script combines YouTube video segment downloading and high-quality encoding into a single automated workflow.

## Features

- ✅ Download specific segments from YouTube videos
- ✅ Automatic encoding to high-quality MP4 (H.264 or H.265)
- ✅ Lossless quality preset for best output
- ✅ Organized folder structure (input/output)
- ✅ Time format support (hr:min:sec, min:sec, or seconds)

## Folder Structure

```
downloadVideo/
├── download_video.py    # Main script
├── input/               # Temporary downloaded segments (.webm)
├── output/              # Final encoded videos (.mp4)
└── README.md            # This file
```

## Requirements

Make sure you have these dependencies installed:

```bash
pip install yt-dlp imageio-ffmpeg
```

## Usage

1. **Edit the configuration** in `download_video.py`:

```python
# Configuration - MODIFY THESE VALUES
VIDEO_URL = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
START_TIME = "1:10:27"  # hr:min:sec format (or "70:27" or "4227")
END_TIME = "1:12:18"

# Optional: Change codec and quality
CODEC = 'h264'      # Options: 'h264' or 'h265'
QUALITY = 'lossless' # Options: 'lossless' or 'high'
```

2. **Run the script**:

```bash
python download_video.py
```

3. **Find your video** in the `output/` folder!

## Time Format Examples

The script accepts multiple time formats:

- `"1:44:00"` - 1 hour, 44 minutes, 0 seconds
- `"44:00"` - 44 minutes, 0 seconds  
- `"2640"` - 2640 seconds (44 minutes)

## How It Works

1. **Download**: Downloads the specified segment from YouTube in WebM format (saved to `input/`)
2. **Encode**: Converts the WebM file to high-quality MP4 using FFmpeg (saved to `output/`)
3. **Cleanup**: Optionally removes the intermediate WebM file

## Quality Settings

### Lossless (Recommended)
- **H.264**: CRF 18, slow preset
- **H.265**: CRF 20, slow preset
- Produces near-visually-lossless output

### High
- **H.264**: CRF 23, medium preset
- **H.265**: CRF 25, medium preset
- Good balance of quality and file size

## Output Format

All videos are encoded with:
- **Video Codec**: H.264 or H.265 (configurable)
- **Audio Codec**: AAC, 192kbps, 48kHz
- **Pixel Format**: YUV 4:2:0 (for compatibility)
- **Container**: MP4 with faststart flag

## Troubleshooting

### "FFmpeg not found"
Install imageio-ffmpeg:
```bash
pip install imageio-ffmpeg
```

### "yt-dlp not found"
Install yt-dlp:
```bash
pip install yt-dlp
```

### Download is slow
This is normal for high-quality videos. The script will show progress.

### Encoding takes long time
Lossless encoding with slow preset prioritizes quality over speed. Use `QUALITY = 'high'` for faster encoding.

## Example

```bash
# Download and encode a 2-minute segment
VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
START_TIME = "0:30"
END_TIME = "2:30"

# Run the script
python download_video.py
```

Output will be saved to: `output/segment_[timestamp].mp4`
