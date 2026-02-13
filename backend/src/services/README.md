# Services Directory - README

This directory contains all service modules for the YouTube Downloader application. Services contain pure business logic with no database operations or UI code.

## Architecture

**Service Layer**: Pure business logic
**Data Layer** (`src/data/`): Database operations, calls services
**Routes** (`src/routes/`): API endpoints, uses data layer
**Standalone Scripts**: Use services directly

## Service Files

### 1. **video_service.py** - Video Download Service

Main service for downloading YouTube video segments using yt-dlp.

**Key Method**: `VideoService.download_video_segment(url, start_time, end_time, output_path, format_preference, resolution_preference, video_id, progress_callback)`

**Parameters**:
- `url`: YouTube video URL
- `start_time`: Start time in seconds
- `end_time`: End time in seconds  
- `output_path`: Path for output file
- `format_preference`: Format (mp4, webm, best)
- `resolution_preference`: Resolution (e.g., 720p, 1080p, 1440p, 2160p, or best)
- `video_id`: Optional video ID for cache storage
- `progress_callback`: Optional callback function for progress updates

**Returns**: `(success: bool, file_path: str, error_message: str)`

**Features**:
- Downloads specific time segments from YouTube videos
- Supports multiple formats (mp4, webm, etc.)
- Supports multiple resolutions  
- Real-time progress tracking via callbacks
- Stores progress in cache (optional)
- Database-agnostic (no DB calls)

**Helper Method**: `_build_format_string(resolution, format_ext)` - Builds yt-dlp format selection string

---

### 2. **encoding_service.py** - Video Encoding Service

Service for encoding videos to MP4 with GPU acceleration support.

**Key Method**: `EncodingService.encode_video_to_mp4(input_path, output_path, video_codec, quality_preset, use_gpu, encode_id, progress_callback)`

**Parameters**:
- `input_path`: Path to input video file
- `output_path`: Path for output MP4 file
- `video_codec`: Codec (h264, h265, av1)
- `quality_preset`: Quality (lossless, high, medium)
- `use_gpu`: Whether to attempt GPU encoding
- `encode_id`: Optional ID for cache storage
- `progress_callback`: Optional callback for progress updates

**Returns**: `(success: bool, error_message: str)`

**Features**:
- GPU acceleration (NVIDIA, AMD, Intel)
- Automatic CPU fallback if GPU fails
- Multiple codec support (H.264, H.265, AV1)
- AV1 → H.265 fallback if codec unavailable
- Quality presets (lossless, high, medium)
- Real-time progress tracking
- Automatic duration detection
- Stores progress in cache (optional)

**Quality Settings**:
- **lossless**: CRF 18 (near-lossless, 2-pass)
- **high**: CRF 23 (high quality)
- **medium**: CRF 28 (medium quality)

**Helper Methods**:
- `validate_video_file(file_path)` - Validates video file
- `_get_quality_params(quality_preset, codec)` - Gets CRF values
- `_build_ffmpeg_command(...)` - Builds FFmpeg command with GPU support

---

### 3. **youtube_service.py** - YouTube API Service

Service for YouTube video ID validation and metadata extraction.

**Methods**:

**`validate_video_id(video_id)`**
- Validates YouTube video ID format (11 characters)
- Returns: `(is_valid: bool, error_message: str)`

**`parse_video_id_from_url(url)`**
- Extracts video ID from various YouTube URL formats
- Supports: youtube.com/watch, youtu.be, youtube.com/embed, youtube.com/v
- Returns: `video_id: str` or `None`

**`construct_video_url(video_id)`**
- Builds standard YouTube URL from video ID
- Returns: `https://www.youtube.com/watch?v={video_id}`

**`get_video_info(video_id)`**
- Fetches video metadata using yt-dlp
- Returns dict with: video_id, title, duration, thumbnail, uploader, upload_date, view_count, is_live, was_live, resolution, formats_available

**`get_available_formats(video_id)`**
- Gets available high-quality resolutions (720p and above) for a video
- Returns: List of resolutions (e.g., `["1440p", "1080p", "720p"]`) or `None`

---

### 4. **ffmpeg_utils_service.py** - FFmpeg Utilities

Shared FFmpeg utilities used by other services.

**Methods**:

**`timestamp_to_seconds(timestamp)`**
- Converts timestamp string to seconds
- Format: "HH:MM:SS" or "MM:SS" or "SS"
- Returns: seconds as int

**`get_ffmpeg_path()`**
- Finds FFmpeg executable path
- Checks: imageio-ffmpeg package, system PATH, common locations
- Returns: `(ffmpeg_path: str, ffmpeg_dir: str)`

**`setup_ffmpeg()`**
- Sets up FFmpeg (downloads if needed via imageio-ffmpeg)
- Returns: `(ffmpeg_path: str, ffmpeg_dir: str)`

**`get_video_duration(ffmpeg_path, video_path)`**
- Gets video duration in seconds using ffprobe
- Returns: `duration: float` or `None`

**`detect_gpu_encoder(ffmpeg_path, codec)`**
- Detects available GPU encoder for a codec
- Checks: NVIDIA (nvenc), AMD (amf), Intel (qsv)
- Returns: `(encoder_name: str, gpu_type: str)` or `(None, None)`

---

### 5. **progress_cache.py** - Progress Cache Service

Stores video processing progress in Redis or local dict fallback.

**Class**: `ProgressCache`

**Methods**:

**`set_progress(video_id, progress_data)`**
- Stores complete progress data for a video
- Data stored with 1-hour TTL
- Keys: download_progress, encoding_progress, current_phase, speed, eta, fps

**`get_progress(video_id)`**
- Retrieves progress data for a video
- Returns: dict with progress data or `None`

**`update_field(video_id, field, value)`**
- Updates a single field in progress data
- Useful for incremental updates

**`delete_progress(video_id)`**
- Deletes progress data for a video

**Features**:
- Uses Redis if available (for multi-server deployments)
- Falls back to local dict if Redis unavailable
- Automatic TTL management (1 hour)
- Thread-safe for local cache

---

### 6. **db_service.py** - Database Service

MongoDB connection management.

**Methods**:

**`get_database()`**
- Returns MongoDB database instance
- Creates connection if needed
- Reuses existing connection (singleton pattern)

---

### 7. **cache_service.py** - Cache Service

Redis cache management for sessions and temporary data.

**Methods**:

**`get_cache_client()`**
- Returns Redis client instance
- Creates connection if needed
- Falls back gracefully if Redis unavailable

---

### 8. **cleanup_service.py** - Cleanup Service

Background service for cleaning up expired video files.

**Functions**:

**`cleanup_expired_videos()`**
- Finds and deletes expired video files
- Runs periodically via scheduler

**`start_cleanup_scheduler()`**
- Starts background cleanup thread
- Runs cleanup every N minutes (configured)

---

### 9. **firebase_service.py** - Firebase Service

Firebase Admin SDK wrapper (singleton pattern).

**Class**: `FirebaseService`

**Methods**:
- `get_auth()` - Returns Firebase Auth instance
- `get_firestore()` - Returns Firestore instance  
- `get_storage()` - Returns Storage instance

**Function**: `get_firebase_service()` - Get singleton instance

---

## Usage Patterns

### For API Endpoints (with Database)

```python
from src.data import VideoData, EncodingData

# Routes use data layer
success, file_path, error = VideoData.download_video(
    video_id,
    format_preference="mp4",
    resolution_preference="1080p"
)
```

### For CLI/Tests (without Database)

```python
from src.services.video_service import VideoService
from src.services.encoding_service import EncodingService

# Use services directly
success, file_path, error = VideoService.download_video_segment(
    url="https://youtube.com/watch?v=...",
    start_time=60,
    end_time=120,
    output_path="output.mp4",
    format_preference="mp4",
    resolution_preference="1080p"
)

success, error = EncodingService.encode_video_to_mp4(
    input_path="input.webm",
    output_path="output.mp4",
    video_codec="h264",
    quality_preset="high",
    use_gpu=True
)
```

### With Progress Callbacks

```python
def my_progress_callback(data):
    if 'percent' in data:
        print(f"Progress: {data['percent']}%")
        print(f"Speed: {data.get('speed', '?')}")
        print(f"ETA: {data.get('eta', '?')}")

VideoService.download_video_segment(
    ...,
    progress_callback=my_progress_callback
)
```

---

## Design Principles

1. **No Database Calls in Services**: Services contain only business logic. Database operations are in the data layer.

2. **Accept Data as Parameters**: Services accept all necessary data as parameters instead of fetching from database.

3. **Single Responsibility**: Each service has a focused purpose.

4. **Callback-Based Progress**: Services use callbacks for progress reporting instead of printing or database updates.

5. **Database-Agnostic**: Services can be used by API (with DB), CLI, or tests (without DB).

6. **GPU Auto-Detection**: Encoding service automatically detects and uses GPU if available, falls back to CPU.

7. **Error Handling**: Services return success/failure with error messages, don't raise exceptions unnecessarily.

---

## Configuration

Services use settings from `src/config.py`:

- `Config.DOWNLOADS_DIR` - Downloads directory
- `Config.UPLOADS_DIR` - Uploads directory
- `Config.DEFAULT_VIDEO_FORMAT` - Default format preference
- `Config.DEFAULT_VIDEO_RESOLUTION` - Default resolution preference
- `Config.MAX_VIDEO_DURATION` - Maximum allowed duration
- `Config.ENCODING_TIMEOUT_SECONDS` - Encoding timeout

---

## Progress Data Format

Progress data stored in cache has this structure:

```python
{
    'download_progress': 75.5,      # Percentage
    'encoding_progress': 50.0,      # Percentage
    'current_phase': 'encoding',    # Phase: downloading, merging, encoding
    'speed': '2.5x',                # Encoding/download speed
    'eta': '01:23',                 # Estimated time remaining
    'fps': 45.2                     # Encoding FPS (encoding only)
}
```

---

## Testing

All services can be tested independently without database:

```bash
# Test download
python tests/test_download.py

# Test encoding
python tests/test_encoding.py

# Test format detection
python tests/test_format_detection.py
```

---

## Dependencies

- **yt-dlp**: YouTube video downloading
- **ffmpeg**: Video encoding and processing
- **imageio-ffmpeg**: FFmpeg binary distribution
- **redis**: Progress caching (optional)
- **pymongo**: MongoDB database
- **firebase-admin**: Firebase services (optional)
