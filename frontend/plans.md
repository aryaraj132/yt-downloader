# YouTube Downloader - Frontend Plans

## Architecture (v2.0)

The application is split into three services:

1. **API Server** (TypeScript/Express) — handles routes, auth, DB, queue management
2. **Worker** (Python) — handles yt-dlp downloads, ffmpeg encoding, S3 uploads
3. **Frontend** (Next.js) — user interface

Communication: API Server ↔ Worker via Redis queues. Progress tracking via Redis hashes.

## Features

### ✅ Implemented
- [x] YouTube video segment downloading (clip by time range)
- [x] Video encoding (H.264, H.265, AV1 with quality presets)
- [x] User authentication (register, login, Google OAuth)
- [x] User dashboard with paginated video history
- [x] Guest mode with rate limiting (public API)
- [x] Real-time progress tracking (download + encoding phases)
- [x] S3 storage with direct download URLs
- [x] Cookie file support for yt-dlp authentication
- [x] Download Center (past 24 hours job history with download links)
- [x] Async job processing via Redis queues

### Future Enhancements
- [ ] Playlist download support
- [ ] Batch download queue
- [ ] Video preview thumbnails
- [ ] Audio-only extraction
- [ ] Webhook notifications for job completion