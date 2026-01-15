# YouTube Video Downloader

A production-ready Python service for downloading YouTube video segments with user authentication and automated cleanup.

## Features

- **User Management**: Register, login, logout, and password management
- **Two-Tier Authentication**: Public tokens for saving video info, private tokens for downloads
- **Video Processing**: Extract specific time segments from YouTube videos using yt-dlp
- **Video Encoding**: Convert any video format to MP4 with H.264, H.265, or AV1 codecs
- **Session Management**: Dual storage in MongoDB and Redis for optimal performance
- **Auto Cleanup**: Automatically delete video files after 30 minutes
- **Production Ready**: Systemd service, proper logging, error handling

## Tech Stack

- **Backend**: Python 3.8+, Flask
- **Database**: MongoDB
- **Cache**: Redis
- **Video Processing**: yt-dlp
- **Config**: Firebase Admin SDK (optional)

## Project Structure

```
yt-downloader/
├── src/
│   ├── models/          # Data models (User, Session, Video)
│   ├── routes/          # API route handlers
│   ├── services/        # Business logic services
│   ├── middleware/      # Authentication middleware
│   ├── utils/           # Utility functions
│   ├── config.py        # Configuration management
│   └── app.py           # Flask application
├── downloads/           # Temporary video storage
├── requirements.txt     # Python dependencies
├── run.py              # Application entry point
└── yt-downloader.service # Systemd service file
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- MongoDB 4.0+
- Redis 5.0+
- yt-dlp (will be installed via pip)
- FFmpeg (required by yt-dlp for video processing)

### Installation

1. **Clone the repository**
   ```bash
   cd /var/www
   git clone <your-repo-url> yt-downloader
   cd yt-downloader
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg** (if not already installed)
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # CentOS/RHEL
   sudo yum install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows: Download from https://ffmpeg.org/download.html
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your configuration
   ```

   Generate secure secrets:
   ```bash
   python -c "import secrets; print('JWT_PUBLIC_SECRET=' + secrets.token_urlsafe(32))"
   python -c "import secrets; print('JWT_PRIVATE_SECRET=' + secrets.token_urlsafe(32))"
   python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"
   ```

6. **Run the application**
   
   Development mode:
   ```bash
   python start_server.py
   ```
   
   Production mode with gunicorn:
   ```bash
   gunicorn -c gunicorn_config.py "start_server:create_application()"
   ```
   
   **Note**: The server will automatically check and setup FFmpeg on first run using the bundled `imageio-ffmpeg` package.

## API Documentation

### Authentication Endpoints

#### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepass123"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepass123"
}

Response:
{
  "token": "eyJ...",
  "user": {
    "id": "...",
    "email": "user@example.com"
  }
}
```

#### Get Public Token
```http
GET /api/auth/token/public

Response:
{
  "token": "eyJ...",
  "expires_in": 86400
}
```

### Video Endpoints

#### Save Video Info
```http
POST /api/video/save
Authorization: Bearer <public_token>
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "start_time": 30,
  "end_time": 90,
  "user_id": "<user_id>"
}

Response:
{
  "video_id": "...",
  "message": "Video info saved successfully"
}
```

#### Download Video
```http
POST /api/video/download/<video_id>
Authorization: Bearer <private_token>

Response: Video file (MP4)
```

#### Get Video Status
```http
GET /api/video/status/<video_id>
Authorization: Bearer <private_token>

Response:
{
  "video_id": "...",
  "status": "completed",
  "file_available": true
}
```

### Video Encoding Endpoints

#### Upload Video for Encoding
```http
POST /api/encode/upload
Authorization: Bearer <private_token>
Content-Type: multipart/form-data

Form Data:
  video: <video_file>

Response:
{
  "encode_id": "...",
  "original_filename": "video.avi",
  "file_size_mb": 45.2,
  "metadata": {
    "duration": 120,
    "resolution": "1920x1080",
    "original_codec": "h264"
  }
}
```

#### Start Encoding
```http
POST /api/encode/start/<encode_id>
Authorization: Bearer <private_token>
Content-Type: application/json

{
  "video_codec": "h264",  // Options: h264, h265, av1
  "quality_preset": "high"  // Options: lossless, high, medium
}

Response:
{
  "message": "Video encoded successfully",
  "encode_id": "...",
  "file_size_mb": 38.5
}
```

#### Get Encoding Status
```http
GET /api/encode/status/<encode_id>
Authorization: Bearer <private_token>

Response:
{
  "encode_id": "...",
  "status": "completed",
  "progress": 100,
  "video_codec": "h264",
  "quality_preset": "high",
  "file_available": true
}
```

#### Download Encoded Video
```http
POST /api/encode/download/<encode_id>
Authorization: Bearer <private_token>

Response: Video file (MP4)
```

#### Get Supported Codecs
```http
GET /api/encode/codecs

Response:
{
  "codecs": {
    "h264": ["lossless", "high", "medium"],
    "h265": ["lossless", "high", "medium"],
    "av1": ["lossless", "high", "medium"]
  }
}
```

## Deployment on Linux Server

### 1. System Setup

```bash
# Create application user
sudo useradd -r -s /bin/false yt-downloader

# Create directories
sudo mkdir -p /var/www/yt-downloader
sudo mkdir -p /var/log/yt-downloader

# Set permissions
sudo chown -R yt-downloader:yt-downloader /var/www/yt-downloader
sudo chown -R yt-downloader:yt-downloader /var/log/yt-downloader
```

### 2. Install Application

```bash
cd /var/www/yt-downloader
sudo -u yt-downloader git clone <your-repo> .
sudo -u yt-downloader python3 -m venv venv
sudo -u yt-downloader venv/bin/pip install -r requirements.txt
```

### 3. Configure Environment

```bash
sudo -u yt-downloader cp .env.example .env
sudo -u yt-downloader nano .env
# Add your production configuration
```

### 4. Setup Systemd Service

```bash
# Copy service file
sudo cp yt-downloader.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable yt-downloader
sudo systemctl start yt-downloader

# Check status
sudo systemctl status yt-downloader
```

### 5. Setup Nginx (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

## Configuration

See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for detailed configuration options.

## Monitoring and Logs

```bash
# View application logs
sudo journalctl -u yt-downloader -f

# View access logs
sudo tail -f /var/log/yt-downloader/access.log

# View error logs
sudo tail -f /var/log/yt-downloader/error.log
```

## Troubleshooting

### Video Download Fails

1. Check yt-dlp is installed: `yt-dlp --version`
2. Check FFmpeg is installed: `ffmpeg -version`
3. Update yt-dlp: `pip install --upgrade yt-dlp`
4. Check logs for specific error messages

### Database Connection Issues

1. Verify MongoDB is running: `sudo systemctl status mongodb`
2. Check connection string in `.env`
3. Ensure MongoDB allows connections from app server

### Redis Connection Issues

1. Verify Redis is running: `sudo systemctl status redis`
2. Check Redis host/port in `.env`
3. Test connection: `redis-cli ping`

## Security Considerations

1. **Change all default secrets** in production
2. **Use HTTPS** with proper SSL certificates
3. **Configure CORS** properly for your domain
4. **Set up firewall rules** to restrict access
5. **Regular security updates** for dependencies
6. **Monitor logs** for suspicious activity
7. **Implement rate limiting** for public endpoints

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
export FLASK_ENV=development
python run.py

# Code formatting
black src/

# Linting
flake8 src/
```

## License

[Add your license here]

## Support

For issues and questions, please create an issue on GitHub or contact [your-email].
