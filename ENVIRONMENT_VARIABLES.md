# YouTube Video Downloader - Environment Variables

This document lists all environment variables required to run the YouTube Video Downloader application.

## Firebase Configuration

### `FIREBASE_SERVICE_ACCOUNT_KEY_PATH`
- **Type**: String (file path)
- **Required**: Optional
- **Default**: `./service-account-key.json`
- **Description**: Path to Firebase Admin SDK service account JSON key file
- **Example**: `/etc/yt-downloader/firebase-key.json`

## MongoDB Configuration

### `MONGODB_URI`
- **Type**: String (connection URI)
- **Required**: Yes
- **Description**: MongoDB connection string
- **Example**: `mongodb://localhost:27017/yt_downloader` or `mongodb+srv://user:pass@cluster.mongodb.net/yt_downloader`

### `MONGODB_DB_NAME`
- **Type**: String
- **Required**: No
- **Default**: `yt_downloader`
- **Description**: MongoDB database name

## Redis Configuration

### `REDIS_URI`
- **Type**: String (connection URI)
- **Required**: No
- **Default**: `redis://localhost:6379/0`
- **Description**: Redis connection URI including host, port, password (if needed), and database number
- **Format**: `redis://[[username:]password@]host[:port][/database]`
- **Examples**: 
  - Local without password: `redis://localhost:6379/0`
  - With password: `redis://:mypassword@localhost:6379/0`
  - Remote server: `redis://redis.example.com:6379/0`
  - With username and password: `redis://user:password@redis.example.com:6379/1`


## JWT Token Configuration

### `JWT_PUBLIC_SECRET`
- **Type**: String
- **Required**: Yes
- **Description**: Secret key for signing public API tokens
- **Example**: `your-random-secret-key-here-min-32-chars`
- **Security**: Generate using: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### `JWT_PRIVATE_SECRET`
- **Type**: String
- **Required**: Yes
- **Description**: Secret key for signing private user tokens
- **Example**: `another-random-secret-key-here-min-32-chars`
- **Security**: Must be different from `JWT_PUBLIC_SECRET`

### `JWT_PUBLIC_EXPIRATION`
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `86400` (24 hours)
- **Description**: Expiration time for public tokens

### `JWT_PRIVATE_EXPIRATION`
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `604800` (7 days)
- **Description**: Expiration time for private user tokens

## Flask Configuration

### `FLASK_SECRET_KEY`
- **Type**: String
- **Required**: Yes
- **Description**: Flask secret key for session management
- **Example**: `flask-secret-key-random-string-min-32-chars`
- **Security**: Generate using: `python -c "import secrets; print(secrets.token_hex(32))"`

### `FLASK_ENV`
- **Type**: String
- **Required**: No
- **Default**: `production`
- **Options**: `development` or `production`
- **Description**: Flask environment mode

### `PORT`
- **Type**: Integer
- **Required**: No
- **Default**: `5000`
- **Description**: Application server port

## Application Configuration

### `DOWNLOADS_DIR`
- **Type**: String (directory path)
- **Required**: No
- **Default**: `./downloads`
- **Description**: Directory for storing temporary video files
- **Note**: Ensure this directory has write permissions

### `MAX_VIDEO_DURATION`
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `3600` (1 hour)
- **Description**: Maximum allowed duration for video segments

### `VIDEO_RETENTION_MINUTES`
- **Type**: Integer (minutes)
- **Required**: No
- **Default**: `30`
- **Description**: How long to keep downloaded video files before auto-deletion

### `CLEANUP_INTERVAL_MINUTES`
- **Type**: Integer (minutes)
- **Required**: No
- **Default**: `5`
- **Description**: How often to run the cleanup task

## Logging Configuration

### `LOG_LEVEL`
- **Type**: String
- **Required**: No
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Application logging level

### `LOG_FILE`
- **Type**: String (file path)
- **Required**: No
- **Default**: `./logs/app.log`
- **Description**: Path to application log file
- **Note**: Ensure the logs directory exists and has write permissions

## Video Download Preferences

### `DEFAULT_VIDEO_FORMAT`
- **Type**: String
- **Required**: No
- **Default**: `mp4`
- **Options**: `mp4`, `webm`, `mkv`, `flv`, `avi`, `m4a`, `mp3`, `ogg`, `wav`, `best`
- **Description**: Default video format for downloads when not specified by user

### `DEFAULT_VIDEO_RESOLUTION`
- **Type**: String
- **Required**: No
- **Default**: `best`
- **Options**: `best`, `worst`, `2160p`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `240p`, `144p`, `4320p`
- **Description**: Default video resolution for downloads when not specified by user

### `YOUTUBE_API_KEY`
- **Type**: String
- **Required**: No
- **Default**: Empty
- **Description**: YouTube Data API v3 key for fetching video metadata (optional feature)
- **Note**: Only needed if you want to use YouTube API for metadata fetching. Most features work without it using yt-dlp.

## Quick Setup Example

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file
nano .env

# Generate secrets
python -c "import secrets; print('JWT_PUBLIC_SECRET=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_PRIVATE_SECRET=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"

# Add the generated secrets to your .env file
```

## Firebase Remote Config (Optional)

If you want to use Firebase Remote Config to manage environment variables:

1. Set up Firebase Remote Config in your Firebase console
2. Add all the above environment variables as parameters
3. The application will automatically fetch these values on startup

Note: Environment variables in `.env` file will take precedence over Firebase Remote Config.
