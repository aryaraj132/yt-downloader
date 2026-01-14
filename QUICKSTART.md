# Quick Start Guide

## For Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your MongoDB and Redis settings

# 3. Start the server (FFmpeg will auto-setup on first run)
python start_server.py
```

## For Production (Linux)

```bash
# 1. Install application
cd /var/www/yt-downloader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
nano .env  # Add production settings

# 3. Test FFmpeg setup
python setup_ffmpeg.py

# 4. Start with systemd
sudo cp yt-downloader.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yt-downloader
sudo systemctl start yt-downloader
sudo systemctl status yt-downloader
```

## How It Works

1. **start_server.py** - Main entrypoint that:
   - Checks if FFmpeg is available
   - If not, copies FFmpeg from imageio-ffmpeg to `bin/` directory
   - Initializes all services (DB, Cache, Cleanup)
   - Starts the Flask application

2. **setup_ffmpeg.py** - Utility script that:
   - Creates `bin/` directory
   - Copies FFmpeg binaries from imageio-ffmpeg package
   - Makes them executable (on Linux)
   - Can be run manually: `python setup_ffmpeg.py`

3. **bin/** directory:
   - Contains FFmpeg binaries
   - Gitignored (not pushed to repo)
   - Auto-created on deployment

## Notes

- No need to install FFmpeg system-wide
- `imageio-ffmpeg` package includes FFmpeg binaries
- Works cross-platform (Windows/Linux/Mac)
- FFmpeg setup is automatic on first run
