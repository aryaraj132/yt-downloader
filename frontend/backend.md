# YouTube Video Downloader - Backend Documentation

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Authentication System](#authentication-system)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Core Services](#core-services)
- [Configuration](#configuration)
- [Deployment](#deployment)

---

## Project Overview

A production-ready Python backend service for downloading YouTube video segments with user authentication, video encoding capabilities, and automated cleanup. The service provides two-tier authentication (public and private tokens), supports multiple video formats and resolutions, enables live stream clipping, and offers video format conversion.

### Key Features

- **User Management**: Full authentication system with register, login, logout, and password management
- **Two-Tier Token System**: 
  - Public tokens for saving video info (public-facing, used in integrations like Nightbot)
  - Private tokens for downloading and encoding operations
- **YouTube Video Processing**: Download specific time segments from YouTube videos
- **Multi-Format Support**: Download videos in various formats (MP4, WebM) and resolutions (720p to 4320p)
- **Live Stream Integration**: Clip segments from live streams using chat timestamps
- **Video Encoding**: Convert any video format to MP4 with H.264, H.265, or AV1 codecs
- **Session Management**: Dual storage in MongoDB and Redis for optimal performance
- **Auto Cleanup**: Automatically delete video files after 30 minutes
- **Real-time Progress Tracking**: Monitor download and encoding progress

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   Client App    │ (Frontend to be built)
│                 │
└────────┬────────┘
         │ HTTP/REST
         │
┌────────▼────────────────────────────────────────┐
│           Flask API Server                      │
│  ┌──────────────────────────────────────────┐  │
│  │  Routes Layer                             │  │
│  │  - Auth Routes    (/api/auth/*)           │  │
│  │  - Video Routes   (/api/video/*)          │  │
│  │  - Encode Routes  (/api/encode/*)         │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  Middleware                               │  │
│  │  - Authentication (Public/Private Token)  │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  Services Layer                           │  │
│  │  - VideoService                           │  │
│  │  - YouTubeService                         │  │
│  │  - EncodingService                        │  │
│  │  - CleanupService                         │  │
│  │  - CacheService                           │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  Models Layer                             │  │
│  │  - User, Session, Video                   │  │
│  └──────────────────────────────────────────┘  │
└────────┬────────────────────┬──────────────────┘
         │                    │
    ┌────▼─────┐         ┌───▼──────┐
    │ MongoDB  │         │  Redis   │
    │ Database │         │  Cache   │
    └──────────┘         └──────────┘
         │
    ┌────▼─────┐
    │ yt-dlp + │
    │ FFmpeg   │
    └──────────┘
```

---

## Technology Stack

- **Backend Framework**: Python 3.8+, Flask
- **Database**: MongoDB 4.0+ (primary data storage)
- **Cache**: Redis 5.0+ (session management and progress tracking)
- **Video Processing**: 
  - yt-dlp (YouTube video downloading)
  - FFmpeg (video encoding and format conversion)
- **Authentication**: JWT (JSON Web Tokens)
- **Password Hashing**: bcrypt
- **Config Management**: Firebase Admin SDK (optional)

---

## Project Structure

```
yt-downloader/
├── src/
│   ├── models/              # Data models
│   │   ├── user.py          # User account model
│   │   ├── session.py       # Session management model
│   │   └── video.py         # Video download/encode requests model
│   │
│   ├── routes/              # API route handlers
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── video.py         # Video download endpoints
│   │   └── encode.py        # Video encoding endpoints
│   │
│   ├── services/            # Business logic services
│   │   ├── video_service.py      # Video download logic
│   │   ├── youtube_service.py    # YouTube API integration
│   │   ├── encoding_service.py   # Video encoding logic
│   │   ├── cleanup_service.py    # Auto-cleanup service
│   │   ├── cache_service.py      # Redis cache operations
│   │   ├── progress_cache.py     # Real-time progress tracking
│   │   ├── db_service.py         # MongoDB operations
│   │   └── ffmpeg_utils_service.py # FFmpeg utilities
│   │
│   ├── middleware/          # Request middleware
│   │   └── auth.py          # Token authentication middleware
│   │
│   ├── utils/               # Utility functions
│   │   ├── token.py         # JWT token generation/validation
│   │   └── validators.py    # Input validation functions
│   │
│   ├── data/                # Data access layer
│   │   ├── video_data.py    # Video data operations
│   │   └── encoding_data.py # Encoding data operations
│   │
│   ├── config.py            # Configuration management
│   └── app.py               # Flask application setup
│
├── downloads/               # Temporary video storage (auto-cleanup)
├── uploads/                 # Temporary upload storage (auto-cleanup)
├── logs/                    # Application logs
├── requirements.txt         # Python dependencies
├── run.py                   # Development entry point
├── start_server.py          # Production entry point
├── gunicorn_config.py       # Gunicorn configuration
└── yt-downloader.service    # Systemd service file
```

---

## Authentication System

### Two-Tier Token System

#### 1. Public Tokens (`/api/auth/token/public`)
- **Purpose**: For saving video info in public-facing scenarios
- **Use Case**: Nightbot commands, webhooks, public integrations
- **Expiration**: 24 hours (configurable)
- **Permissions**: Can only save video info, cannot download
- **Format**: JWT signed with `JWT_PUBLIC_SECRET`

#### 2. Private Tokens (Login endpoint)
- **Purpose**: Full user authentication
- **Use Case**: Video downloads, encoding, account management
- **Expiration**: 7 days (configurable)
- **Permissions**: Full access to user's resources
- **Format**: JWT signed with `JWT_PRIVATE_SECRET`
- **Storage**: Both MongoDB (sessions collection) and Redis cache

### Token Structure

```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "session_id": "507f1f77bcf86cd799439012",
  "type": "private",
  "exp": 1735123456
}
```

### Session Management

Sessions are stored in both MongoDB and Redis:
- **MongoDB**: Persistent storage for session data
- **Redis**: Fast lookup for authentication checks
- **Cleanup**: Invalid sessions removed on logout or password change

---

## Database Schema

### MongoDB Collections

#### 1. `users` Collection

```javascript
{
  "_id": ObjectId("..."),
  "email": "user@example.com",
  "password_hash": "bcrypt_hash_here",
  "created_at": ISODate("2026-01-18T10:00:00Z"),
  "updated_at": ISODate("2026-01-18T10:00:00Z")
}
```

**Indexes**: 
- `email` (unique)

---

#### 2. `sessions` Collection

```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "token": "jwt_token_string",
  "created_at": ISODate("2026-01-18T10:00:00Z"),
  "expires_at": ISODate("2026-01-25T10:00:00Z")
}
```

**Indexes**: 
- `token` (unique)
- `user_id`
- `expires_at` (TTL index)

---

#### 3. `videos` Collection

This collection stores both video download requests and encoding requests.

```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  
  // Source information
  "source_type": "youtube",  // or "upload"
  "url": "https://youtube.com/watch?v=...",  // For YouTube videos
  "youtube_video_id": "dQw4w9WgXcQ",
  
  // Time range (for YouTube downloads)
  "start_time": 60,      // seconds
  "end_time": 120,       // seconds
  
  // Processing status
  "status": "pending",   // pending | processing | completed | failed
  "file_path": "/path/to/video.mp4",
  "error_message": null,
  
  // Format preferences (for downloads)
  "format_preference": "mp4",      // mp4 | webm | best
  "resolution_preference": "1080p", // 720p | 1080p | 1440p | 2160p | best
  "available_formats": ["1440p", "1080p", "720p"],  // Available at save time
  
  // For encoding requests
  "original_filename": "myvideo.avi",
  "input_file_path": "/path/to/uploaded.avi",
  "video_codec": "h264",       // h264 | h265 | av1
  "audio_codec": "aac",
  "quality_preset": "high",    // lossless | high | medium
  "encoding_progress": 0,      // 0-100
  "encoding_started_at": ISODate("..."),
  "encoding_completed_at": ISODate("..."),
  
  // Live stream specific
  "additional_message": "Great moment!",
  "clip_offset": 60,  // seconds before/after
  
  // Metadata
  "file_size_bytes": 52428800,
  "created_at": ISODate("2026-01-18T10:00:00Z"),
  "expires_at": ISODate("2026-01-18T10:30:00Z")  // 30 min after completion
}
```

**Indexes**: 
- `user_id`
- `status`
- `expires_at` (for cleanup)

---

### Redis Cache Structure

#### 1. Session Cache
```
Key: session:{token_hash}
Value: {
  "user_id": "507f1f77bcf86cd799439011",
  "email": "user@example.com"
}
Expiration: 7 days
```

#### 2. Progress Cache
```
Key: progress:{video_id}
Value: {
  "current_phase": "downloading",  // downloading | encoding | initializing
  "download_progress": 45.2,       // 0-100
  "encoding_progress": 0,          // 0-100
  "speed": "2.3x",
  "eta": "03:24",
  "fps": 45.2
}
Expiration: 1 hour
```

---

## API Endpoints

### Base URL
```
http://localhost:5000/api
```

### Authentication Header
```
Authorization: Bearer {token}
```

---

## Authentication Endpoints

### 1. Register User

**Endpoint**: `POST /api/auth/register`

**Description**: Create a new user account

**Authentication**: None

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Validation**:
- Email must be valid format
- Password must be at least 8 characters
- Email must be unique

**Response** (201 Created):
```json
{
  "message": "User registered successfully",
  "user_id": "507f1f77bcf86cd799439011"
}
```

**Error Responses**:
- 400: Invalid email/password format
- 409: Email already registered
- 500: Internal server error

---

### 2. Login

**Endpoint**: `POST /api/auth/login`

**Description**: Authenticate user and create session

**Authentication**: None

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com"
  }
}
```

**Error Responses**:
- 400: Missing email or password
- 401: Invalid credentials
- 500: Internal server error

---

### 3. Logout

**Endpoint**: `POST /api/auth/logout`

**Description**: Invalidate current session

**Authentication**: Private token required

**Request Headers**:
```
Authorization: Bearer {private_token}
```

**Response** (200 OK):
```json
{
  "message": "Logout successful"
}
```

---

### 4. Change Password

**Endpoint**: `POST /api/auth/change-password`

**Description**: Update user password (invalidates all sessions)

**Authentication**: Private token required

**Request Body**:
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewSecurePass456!"
}
```

**Response** (200 OK):
```json
{
  "message": "Password changed successfully. Please login again."
}
```

**Error Responses**:
- 400: Invalid password format
- 401: Current password incorrect
- 500: Internal server error

---

### 5. Get Public Token

**Endpoint**: `GET /api/auth/token/public`

**Description**: Get a public API token for saving video info

**Authentication**: None (public endpoint)

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400
}
```

**Use Case**: Use this token for public integrations like Nightbot commands

---

### 6. Get Current User

**Endpoint**: `GET /api/auth/me`

**Description**: Get current authenticated user info

**Authentication**: Private token required

**Response** (200 OK):
```json
{
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com"
  }
}
```

---

## Video Endpoints

### 1. Save Video Info

**Endpoint**: `POST /api/video/save`

**Description**: Save video download request for later processing

**Authentication**: Public token required

**Request Headers**:
```
Authorization: Bearer {public_token}
```

**Request Body**:
```json
{
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "start_time": 60,
  "end_time": 120,
  "user_id": "507f1f77bcf86cd799439011",
  "additional_message": "Optional description",
  "clip_offset": 30
}
```

**Parameters**:
- `url` (required): YouTube video URL
- `start_time` (required): Start time in seconds
- `end_time` (required): End time in seconds
- `user_id` (required): User ID who owns this request
- `additional_message` (optional): Description or note
- `clip_offset` (optional): For live streams, offset from timestamp

**Response** (201 Created):
```json
{
  "message": "Video info saved successfully",
  "video_id": "507f1f77bcf86cd799439013"
}
```

**Error Responses**:
- 400: Invalid URL, time range, or missing required fields
- 401: Invalid or expired public token
- 500: Internal server error

---

### 2. Save Video from Stream (Nightbot Integration)

**Endpoint**: `GET|POST /api/video/save/stream/{token}/{video_id}`

**Description**: Save video clip from live stream using video ID and query parameters (designed for Nightbot)

**Authentication**: Public token in URL path

**URL Parameters**:
- `token`: Public API token
- `video_id`: YouTube video ID (11 characters)

**Query Parameters**:
- `user_id` (required): User ID
- `message` (optional): User message/description
- `offset` (optional): Seconds to capture before/after timestamp (default: 60)
- `duration` (optional): Total clip duration in seconds (default: 120)

**Example Nightbot Command**:
```
$(urlfetch https://api.example.com/api/video/save/stream/$(token)/$(chatid)?user_id=12345&message=$(querystring))
```

**Response** (201 Created):
```json
{
  "message": "Video clip saved successfully",
  "video_id": "507f1f77bcf86cd799439013",
  "youtube_video_id": "dQw4w9WgXcQ"
}
```

---

### 3. Download Video

**Endpoint**: `POST /api/video/download/{video_id}`

**Description**: Download video with optional format and resolution preferences

**Authentication**: Private token required

**URL Parameters**:
- `video_id`: Video document ID from save endpoint

**Request Body** (Optional):
```json
{
  "format_preference": "mp4",
  "resolution_preference": "1080p"
}
```

**Format Options**: `mp4`, `webm`, `best`
**Resolution Options**: `720p`, `1080p`, `1440p`, `2160p`, `4320p`, `best`

**Smart Download Logic**:
- For ≤1080p: Downloads directly in preferred format
- For ≥1440p with MP4 preference:
  1. Downloads as WebM
  2. Encodes to H.265 lossless MP4
- Updates status to "processing" during download

**Response** (200 OK):
- **Content-Type**: `video/mp4`
- **Content-Disposition**: `attachment; filename="video_{video_id}.mp4"`
- Binary video file

**Alternative Response** (202 Accepted) - if still processing:
```json
{
  "message": "Video is currently being processed",
  "status": "processing"
}
```

**Error Responses**:
- 403: Unauthorized (not video owner)
- 404: Video not found
- 500: Download failed

---

### 4. Get Video Status

**Endpoint**: `GET /api/video/status/{video_id}`

**Description**: Get video processing status with real-time progress

**Authentication**: Private token required

**Response** (200 OK):
```json
{
  "video_id": "507f1f77bcf86cd799439013",
  "status": "processing",
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "start_time": 60,
  "end_time": 120,
  "created_at": "2026-01-18T10:00:00Z",
  "file_available": false,
  "available_formats": ["1440p", "1080p", "720p"],
  "progress": {
    "current_phase": "downloading",
    "download_progress": 45.2,
    "encoding_progress": 0,
    "speed": "2.3x",
    "eta": "03:24",
    "fps": 45.2
  }
}
```

**Status Values**:
- `pending`: Saved but not yet started
- `processing`: Currently downloading or encoding
- `completed`: Ready for download
- `failed`: Error occurred

---

### 5. List User Videos

**Endpoint**: `GET /api/video/list`

**Description**: Get all videos for authenticated user

**Authentication**: Private token required

**Response** (200 OK):
```json
{
  "videos": [
    {
      "video_id": "507f1f77bcf86cd799439013",
      "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "start_time": 60,
      "end_time": 120,
      "status": "completed",
      "created_at": "2026-01-18T10:00:00Z",
      "file_available": true
    }
  ]
}
```

---

### 6. Get Available Formats

**Endpoint**: `GET /api/video/formats/{video_id}`

**Description**: Get available formats and resolutions for a video

**Authentication**: Private token required

**URL Parameters**:
- `video_id`: Can be either a video document ID or YouTube video ID

**Response** (200 OK):
```json
{
  "video_id": "dQw4w9WgXcQ",
  "resolutions": ["1440p", "1080p", "720p"],
  "extensions": ["mp4", "webm"],
  "formats": {
    "1440p": ["webm"],
    "1080p": ["mp4", "webm"],
    "720p": ["mp4", "webm"]
  }
}
```

---

### 7. Get Available Resolutions (Public)

**Endpoint**: `POST /api/video/resolutions`

**Description**: Get available resolutions for a YouTube video URL without authentication

**Authentication**: None (public endpoint)

**Request Body**:
```json
{
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response** (200 OK):
```json
{
  "video_id": "dQw4w9WgXcQ",
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "resolutions": ["1440p", "1080p", "720p"]
}
```

**Use Case**: This public endpoint allows frontend applications to check available resolutions for a video before the user registers or logs in. Useful for showing resolution options during video selection.

**Error Responses**:
- 400: Invalid YouTube URL or missing URL parameter
- 500: Failed to retrieve resolutions

---

## Video Encoding Endpoints

### 1. Upload Video for Encoding

**Endpoint**: `POST /api/encode/upload`

**Description**: Upload a video file for encoding to MP4

**Authentication**: Private token required

**Request**:
- **Content-Type**: `multipart/form-data`
- **Form Field**: `video` (video file)

**Allowed Formats**: 
`mp4`, `avi`, `mkv`, `mov`, `flv`, `wmv`, `webm`, `m4v`, `mpg`, `mpeg`, `3gp`

**Max Size**: 500MB (configurable via `MAX_UPLOAD_SIZE_MB`)

**Response** (201 Created):
```json
{
  "message": "Video uploaded successfully",
  "encode_id": "507f1f77bcf86cd799439014",
  "original_filename": "myvideo.avi",
  "file_size_mb": 45.2,
  "metadata": {
    "duration": 120,
    "resolution": "1920x1080",
    "original_codec": "h264"
  }
}
```

**Error Responses**:
- 400: No file, invalid format, or file too large
- 500: Upload failed

---

### 2. Start Encoding

**Endpoint**: `POST /api/encode/start/{encode_id}`

**Description**: Start encoding a video with specified codec and quality

**Authentication**: Private token required

**Request Body**:
```json
{
  "video_codec": "h264",
  "quality_preset": "high"
}
```

**Video Codec Options**:
- `h264`: H.264/AVC (widely compatible)
- `h265`: H.265/HEVC (better compression)
- `av1`: AV1 (best compression, slower)

**Quality Preset Options**:
- `lossless`: Maximum quality, larger file size
- `high`: Near-lossless, balanced
- `medium`: Good quality, smaller file size

**Audio Codec**: Always AAC (automatic)

**Response** (200 OK):
```json
{
  "message": "Video encoded successfully",
  "encode_id": "507f1f77bcf86cd799439014",
  "file_size_mb": 38.5
}
```

**Alternative Response** (202 Accepted):
```json
{
  "message": "Video is currently being encoded",
  "status": "processing"
}
```

**Error Responses**:
- 400: Invalid codec or quality preset
- 403: Unauthorized (not owner)
- 404: Encode request not found
- 500: Encoding failed

---

### 3. Get Encoding Status

**Endpoint**: `GET /api/encode/status/{encode_id}`

**Description**: Get encoding status and progress

**Authentication**: Private token required

**Response** (200 OK):
```json
{
  "encode_id": "507f1f77bcf86cd799439014",
  "status": "processing",
  "progress": 67,
  "original_filename": "myvideo.avi",
  "video_codec": "h264",
  "quality_preset": "high",
  "created_at": "2026-01-18T10:00:00Z",
  "encoding_started_at": "2026-01-18T10:05:00Z",
  "file_available": false,
  "file_size_mb": 38.5
}
```

---

### 4. Download Encoded Video

**Endpoint**: `POST /api/encode/download/{encode_id}`

**Description**: Download the encoded video file

**Authentication**: Private token required

**Response** (200 OK):
- **Content-Type**: `video/mp4`
- **Content-Disposition**: `attachment; filename="myvideo_h264_high.mp4"`
- Binary video file

**Error Responses**:
- 202: Still encoding
- 404: Encode request or file not found
- 500: Encoding failed

---

### 5. Get Supported Codecs

**Endpoint**: `GET /api/encode/codecs`

**Description**: Get list of supported codecs and quality presets

**Authentication**: None (public endpoint)

**Response** (200 OK):
```json
{
  "codecs": {
    "h264": ["lossless", "high", "medium"],
    "h265": ["lossless", "high", "medium"],
    "av1": ["lossless", "high", "medium"]
  }
}
```

---

## Core Services

### 1. VideoService

**File**: `src/services/video_service.py`

**Purpose**: Handle YouTube video downloads using yt-dlp

**Key Methods**:

#### `download_video_segment()`
Downloads a specific segment of a YouTube video with format and resolution preferences.

**Smart Download Logic**:
- For resolutions ≤1080p: Downloads directly in preferred format
- For resolutions ≥1440p requesting MP4:
  1. Downloads as WebM (YouTube's native high-res format)
  2. Encodes to H.265 lossless MP4 using FFmpeg
- Supports real-time progress tracking via callbacks

**Parameters**:
- `url`: YouTube video URL
- `start_time`: Start time in seconds
- `end_time`: End time in seconds
- `output_path`: Where to save the file
- `format_preference`: `mp4` | `webm` | `best`
- `resolution_preference`: `720p` | `1080p` | `1440p` | `2160p` | `best`
- `video_id`: Optional video ID for progress tracking
- `progress_callback`: Optional callback for progress updates

---

### 2. YouTubeService

**File**: `src/services/youtube_service.py`

**Purpose**: YouTube-specific operations and metadata fetching

**Key Methods**:

#### `validate_video_id(video_id)`
Validates YouTube video ID format (11 characters).

#### `parse_video_id_from_url(url)`
Extracts video ID from various YouTube URL formats.

#### `get_video_info(video_id)`
Fetches video metadata using yt-dlp:
- Title, duration, thumbnail
- Uploader, upload date, view count
- Live stream status

#### `get_available_formats(video_id)`
Returns available high-quality formats (≥720p) for a video.

**Returns**:
```python
["1440p", "1080p", "720p"]  # Sorted highest to lowest
```

---

### 3. EncodingService

**File**: `src/services/encoding_service.py`

**Purpose**: Video encoding and format conversion using FFmpeg

**Key Methods**:

#### `encode_video_to_mp4()`
Encodes video to MP4 with specified codec and quality.

**Codec Settings**:
- **H.264**: 
  - Lossless: `-crf 0`
  - High: `-crf 18`
  - Medium: `-crf 23`
- **H.265**: 
  - Lossless: `-crf 0`
  - High: `-crf 20`
  - Medium: `-crf 28`
- **AV1**: 
  - Lossless: `-crf 0`
  - High: `-crf 23`
  - Medium: `-crf 30`

**Audio**: Always AAC with bitrate 192k

#### `validate_video_file(file_path)`
Validates uploaded video file using FFmpeg.

#### `get_video_metadata(file_path)`
Extracts metadata: duration, resolution, codec, bitrate.

---

### 4. CleanupService

**File**: `src/services/cleanup_service.py`

**Purpose**: Automatically delete expired video files

**Behavior**:
- Runs every 5 minutes (configurable via `CLEANUP_INTERVAL_MINUTES`)
- Deletes video files that have exceeded retention time (30 minutes by default)
- Removes both source and encoded files
- Updates database to reflect file deletion

**Cleanup Logic**:
1. Query MongoDB for videos where `expires_at` ≤ current time
2. Delete physical files from disk
3. Delete database records
4. Log cleanup operations

---

### 5. ProgressCache

**File**: `src/services/progress_cache.py`

**Purpose**: Real-time progress tracking using Redis

**Key Methods**:

#### `set_progress(video_id, progress_data)`
Store progress information in Redis with 1-hour expiration.

#### `get_progress(video_id)`
Retrieve current progress for a video.

**Progress Data Structure**:
```python
{
    "current_phase": "downloading",  # downloading | encoding | initializing
    "download_progress": 45.2,       # 0-100
    "encoding_progress": 0,          # 0-100
    "speed": "2.3x",
    "eta": "03:24",
    "fps": 45.2
}
```

---

## Configuration

### Environment Variables

All configuration is managed via environment variables. See `ENVIRONMENT_VARIABLES.md` for complete details.

#### Required Variables

```bash
# MongoDB
MONGODB_URI=mongodb://localhost:27017/yt_downloader

# JWT Secrets (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_PUBLIC_SECRET=your-public-secret-here
JWT_PRIVATE_SECRET=your-private-secret-here

# Flask
FLASK_SECRET_KEY=your-flask-secret-here
```

#### Important Optional Variables

```bash
# Redis
REDIS_URI=redis://localhost:6379/0


# Application
DOWNLOADS_DIR=./downloads
UPLOADS_DIR=./uploads
MAX_VIDEO_DURATION=3600          # 1 hour max
MAX_UPLOAD_SIZE_MB=500           # 500MB max upload
VIDEO_RETENTION_MINUTES=30       # Auto-delete after 30 min
CLEANUP_INTERVAL_MINUTES=5       # Cleanup runs every 5 min

# Default Preferences
DEFAULT_VIDEO_FORMAT=mp4
DEFAULT_VIDEO_RESOLUTION=1080p

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

---

## Deployment

### Prerequisites

- Python 3.8+
- MongoDB 4.0+
- Redis 5.0+
- FFmpeg (required for video processing)
- yt-dlp (installed via pip)

### Installation Steps

1. **Clone Repository**
```bash
git clone <your-repo-url> yt-downloader
cd yt-downloader
```

2. **Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Install FFmpeg**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html
```

5. **Configure Environment**
```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

6. **Generate Secrets**
```bash
python -c "import secrets; print('JWT_PUBLIC_SECRET=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_PRIVATE_SECRET=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"
```

7. **Run Application**

Development:
```bash
python start_server.py
```

Production (with Gunicorn):
```bash
gunicorn -c gunicorn_config.py "start_server:create_application()"
```

### Systemd Service Setup

1. Copy service file:
```bash
sudo cp yt-downloader.service /etc/systemd/system/
```

2. Edit service file with correct paths:
```bash
sudo nano /etc/systemd/system/yt-downloader.service
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable yt-downloader
sudo systemctl start yt-downloader
sudo systemctl status yt-downloader
```

### Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Important for large file uploads and downloads
        client_max_body_size 500M;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

---

## Frontend Development Guide

### Essential Information for Frontend Developers

#### 1. Authentication Flow

```
1. User Registration
   POST /api/auth/register → Get user_id

2. User Login
   POST /api/auth/login → Get private_token
   Store token in localStorage/sessionStorage

3. Get Public Token (for integrations)
   GET /api/auth/token/public → Get public_token

4. All subsequent requests
   Include: Authorization: Bearer {private_token}
```

#### 2. Video Download Workflow

```
1. Save Video Info
   POST /api/video/save (with public token)
   → Get video_id

2. Poll for Status (optional)
   GET /api/video/status/{video_id}
   → Check if processing/completed

3. Download Video
   POST /api/video/download/{video_id}
   → Receive video file

4. File Auto-Deletes after 30 minutes
```

#### 3. Video Encoding Workflow

```
1. Upload Video
   POST /api/encode/upload
   → Get encode_id

2. Start Encoding
   POST /api/encode/start/{encode_id}
   With codec and quality preferences

3. Poll Status
   GET /api/encode/status/{encode_id}
   → Check progress (0-100)

4. Download Encoded Video
   POST /api/encode/download/{encode_id}
   → Receive encoded MP4
```

#### 4. Real-Time Progress Tracking

For download/encoding operations, poll the status endpoint every 2-3 seconds:

```javascript
const pollProgress = async (videoId) => {
  const response = await fetch(`/api/video/status/${videoId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const data = await response.json();
  
  if (data.status === 'processing' && data.progress) {
    // Update UI with progress
    console.log(`Phase: ${data.progress.current_phase}`);
    console.log(`Progress: ${data.progress.download_progress}%`);
    console.log(`ETA: ${data.progress.eta}`);
  }
};
```

#### 5. Error Handling

Always handle these HTTP status codes:
- **401**: Token expired or invalid → Redirect to login
- **403**: Unauthorized access → Show error
- **404**: Resource not found → Show error
- **500**: Server error → Retry or show error

#### 6. File Download Handling

For download endpoints that return files:

```javascript
const downloadVideo = async (videoId) => {
  const response = await fetch(`/api/video/download/${videoId}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `video_${videoId}.mp4`;
    a.click();
  }
};
```

---

## Support & Troubleshooting

### Common Issues

1. **Video Download Fails**
   - Check yt-dlp is installed: `yt-dlp --version`
   - Update yt-dlp: `pip install --upgrade yt-dlp`
   - Check FFmpeg is installed: `ffmpeg -version`

2. **Database Connection Issues**
   - Verify MongoDB is running: `sudo systemctl status mongodb`
   - Check connection string in `.env`

3. **Redis Connection Issues**
   - Verify Redis is running: `sudo systemctl status redis`
   - Test connection: `redis-cli ping`

### Logs

```bash
# Application logs
tail -f logs/app.log

# Systemd service logs
sudo journalctl -u yt-downloader -f
```

---

## API Summary Table

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | None | Register new user |
| `/api/auth/login` | POST | None | Login user |
| `/api/auth/logout` | POST | Private | Logout user |
| `/api/auth/change-password` | POST | Private | Change password |
| `/api/auth/token/public` | GET | None | Get public token |
| `/api/auth/me` | GET | Private | Get current user |
| `/api/video/save` | POST | Public | Save video info |
| `/api/video/save/stream/{token}/{video_id}` | GET/POST | URL | Save stream clip |
| `/api/video/download/{video_id}` | POST | Private | Download video |
| `/api/video/status/{video_id}` | GET | Private | Get video status |
| `/api/video/list` | GET | Private | List user videos |
| `/api/video/formats/{video_id}` | GET | Private | Get available formats |
| `/api/encode/upload` | POST | Private | Upload video |
| `/api/encode/start/{encode_id}` | POST | Private | Start encoding |
| `/api/encode/status/{encode_id}` | GET | Private | Get encoding status |
| `/api/encode/download/{encode_id}` | POST | Private | Download encoded video |
| `/api/encode/codecs` | GET | None | Get supported codecs |

---

## Additional Notes

- **Video Retention**: All video files are automatically deleted 30 minutes after download/encoding completion
- **Max Video Duration**: Video segments cannot exceed 1 hour (configurable)
- **Max Upload Size**: Video uploads limited to 500MB (configurable)
- **Format Support**: Supports all major video formats for encoding
- **Live Streams**: Can clip segments from live streams using chat timestamps
- **Progress Tracking**: Real-time progress available for all long-running operations

---

## Version & Updates

This backend is production-ready and actively maintained. Keep yt-dlp updated regularly as YouTube frequently changes their API:

```bash
pip install --upgrade yt-dlp
```

---

**Last Updated**: January 2026
**API Version**: 1.0
**Python Version**: 3.8+
