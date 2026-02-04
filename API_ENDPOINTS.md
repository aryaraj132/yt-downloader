# API Endpoint Mapping Documentation

This document maps all frontend API calls to their corresponding backend endpoints.

## Architecture Overview

The frontend uses a **proxy architecture** where all API calls go through Next.js API routes (`/app/api/*`), which then forward requests to the Flask backend using the `proxyToBackend` utility.

### Configuration
- **Frontend Base URL**: `/api` (relative to Next.js app)
- **Backend URL**: `http://localhost:5000` (configurable via `BACKEND_URL` environment variable)

---

## Authentication Endpoints (`/api/auth`)

| Frontend Service Call | Frontend Route | Backend Endpoint | Method | Auth Required |
|----------------------|----------------|------------------|--------|---------------|
| `authService.register()` | `/api/auth/register` | `/api/auth/register` | POST | No |
| `authService.login()` | `/api/auth/login` | `/api/auth/login` | POST | No |
| `authService.logout()` | `/api/auth/logout` | `/api/auth/logout` | POST | Yes (Private) |
| `authService.changePassword()` | `/api/auth/change-password` | `/api/auth/change-password` | POST | Yes (Private) |
| `authService.getPublicToken()` | `/api/auth/token/public` | `/api/auth/token/public` | GET | Yes (Private) |
| `authService.getCurrentUser()` | `/api/auth/me` | `/api/auth/me` | GET | Yes (Private) |
| `authService.initiateGoogleLogin()` | `/api/auth/google/login` | `/api/auth/google/login` | GET | No |
| `authService.handleGoogleCallback()` | `/api/auth/google/callback` | `/api/auth/google/callback` | POST | No |
| `authService.refreshToken()` | `/api/auth/refresh-token` | `/api/auth/refresh-token` | POST | Yes (Private) |

**Frontend Route Handler**: `frontend/app/api/auth/[...path]/route.ts`

---

## Video Endpoints (`/api/video`)

| Frontend Service Call | Frontend Route | Backend Endpoint | Method | Auth Required |
|----------------------|----------------|------------------|--------|---------------|
| `videoService.saveVideoInfo()` | `/api/video/save` | `/api/video/save` | POST | Yes (Public Token) |
| `videoService.getAvailableResolutions()` | `/api/video/resolutions` | `/api/video/resolutions` | POST | No |
| `videoService.downloadVideo()` | `/api/video/download/{videoId}` | `/api/video/download/{videoId}` | POST | Yes (Private) |
| `videoService.getVideoStatus()` | `/api/video/status/{videoId}` | `/api/video/status/{videoId}` | GET | Yes (Private) |
| `videoService.listUserVideos()` | `/api/video/list` | `/api/video/list` | GET | Yes (Private) |
| `videoService.getAvailableFormats()` | `/api/video/formats` | `/api/video/formats` | POST | Yes (Private) |

**Frontend Route Handler**: `frontend/app/api/video/[...path]/route.ts`

**Special Routes**:
- Stream save: `/api/video/save/stream/{token}/{chat_id}` (GET/POST)
- Formats by ID: `/api/video/formats/{video_id}` (GET)

---

## Encode Endpoints (`/api/encode`)

| Frontend Service Call | Frontend Route | Backend Endpoint | Method | Auth Required |
|----------------------|----------------|------------------|--------|---------------|
| `encodeService.uploadVideo()` | `/api/encode/upload` | `/api/encode/upload` | POST | Yes (Private) |
| `encodeService.startEncoding()` | `/api/encode/start/{encodeId}` | `/api/encode/start/{encodeId}` | POST | Yes (Private) |
| `encodeService.getEncodingStatus()` | `/api/encode/status/{encodeId}` | `/api/encode/status/{encodeId}` | GET | Yes (Private) |
| `encodeService.downloadEncodedVideo()` | `/api/encode/download/{encodeId}` | `/api/encode/download/{encodeId}` | POST | Yes (Private) |
| `encodeService.getSupportedCodecs()` | `/api/encode/codecs` | `/api/encode/codecs` | GET | No |

**Frontend Route Handler**: `frontend/app/api/encode/[...path]/route.ts`

---

## Public API Endpoints (`/api/public`) ✅ NEWLY ADDED

| Frontend Service Call | Frontend Route | Backend Endpoint | Method | Auth Required |
|----------------------|----------------|------------------|--------|---------------|
| `videoService.savePublicClip()` | `/api/public/clip` | `/api/public/clip` | POST | No (Rate Limited) |
| `encodeService.encodePublic()` | `/api/public/encode` | `/api/public/encode` | POST | No (Rate Limited) |
| `videoService.getPublicJobStatus()` | `/api/public/status/{jobId}` | `/api/public/status/{jobId}` | GET | No |
| `videoService.downloadPublicFile()` | `/api/public/download/{jobId}` | `/api/public/download/{jobId}` | GET | No |
| `videoService.checkRateLimit()` | `/api/public/rate-limit` | `/api/public/rate-limit` | GET | No (Rate Limited) |

**Frontend Route Handler**: `frontend/app/api/public/[...path]/route.ts` ✅ **CREATED**

**Rate Limiting**: Public API endpoints are rate-limited by IP + browser fingerprint via the `X-Browser-Fingerprint` header.

**Restrictions**:
- Max clip duration: Configured via `PUBLIC_API_MAX_CLIP_DURATION`
- Max encode duration: Configured via `PUBLIC_API_MAX_ENCODE_DURATION`
- Daily limit: Configured via `PUBLIC_API_RATE_LIMIT`

---

## Nightbot Endpoints (`/api/nightbot`)

| Backend Endpoint | Method | Auth Required |
|-----------------|--------|---------------|
| `/api/nightbot/clip` | GET/POST | No |

**Note**: Nightbot endpoints are backend-only and not typically called directly from the frontend.

---

## Request Flow

### Authenticated Requests (Private API)
```
Frontend Service (authService, videoService, encodeService)
  ↓
Next.js API Route (/app/api/{service}/[...path]/route.ts)
  ↓ (adds Authorization header with JWT token from localStorage)
proxyToBackend() utility
  ↓ (forwards to BACKEND_URL with headers)
Flask Backend (/api/{service}/*)
  ↓ (validates JWT token via @require_private_token)
Route Handler + Service Logic
```

### Public API Requests (Guest Mode)
```
Frontend Service (videoService.savePublicClip, encodeService.encodePublic)
  ↓
Next.js API Route (/app/api/public/[...path]/route.ts)
  ↓ (adds X-Browser-Fingerprint header)
proxyToBackend() utility
  ↓ (forwards to BACKEND_URL with headers)
Flask Backend (/api/public/*)
  ↓ (applies rate limiting via @require_public_rate_limit)
Route Handler + Service Logic
```

---

## Special Headers

### Authorization Header
- **Source**: Added by `lib/api.ts` axios interceptor
- **Value**: `Bearer {JWT_TOKEN}` from localStorage
- **Used For**: Private API authentication

### X-Browser-Fingerprint Header
- **Source**: Added by `lib/api.ts` publicApi interceptor
- **Value**: JSON string with browser fingerprint data
- **Used For**: Public API rate limiting

### Content-Type Header
- **JSON requests**: `application/json`
- **File uploads**: `multipart/form-data`

---

## Troubleshooting

### 404 Errors
- ✅ **Fixed**: Created missing `/api/public/[...path]/route.ts`
- Verify `BACKEND_URL` is set in `frontend/.env.local`
- Check that backend server is running on the configured port
- Ensure Next.js dev server is restarted after adding new route files

### 502 Bad Gateway
- Backend service is not running or unreachable
- Check `BACKEND_URL` configuration
- Verify backend is listening on the correct port

### 401 Unauthorized
- Missing or invalid JWT token
- Token expired (check `JWT_PRIVATE_EXPIRATION` in backend)
- Clear localStorage and login again

### 429 Too Many Requests
- Public API rate limit exceeded
- Check remaining quota via `/api/public/rate-limit`
- Wait for rate limit reset or upgrade to authenticated user

---

## Testing Checklist

### Authentication Flow
- [ ] Register new user
- [ ] Login with credentials
- [ ] Get current user info
- [ ] Generate public token
- [ ] Logout

### Video Clipping (Authenticated)
- [ ] Save video info
- [ ] Check video status
- [ ] Download video
- [ ] List user videos

### Video Clipping (Guest/Public)
- [ ] Check rate limit
- [ ] Submit public clip request
- [ ] Check job status
- [ ] Download completed clip

### Video Encoding (Authenticated)
- [ ] Upload video file
- [ ] Start encoding job
- [ ] Check encoding status
- [ ] Download encoded video

### Video Encoding (Guest/Public)
- [ ] Check rate limit
- [ ] Submit public encode request
- [ ] Check job status
- [ ] Download encoded video

---

## Environment Variables

### Frontend (.env.local)
```bash
# Backend URL for API proxy
BACKEND_URL=http://localhost:5000
```

### Backend (.env)
```bash
# Flask configuration
FLASK_SECRET_KEY=<secret>
FLASK_ENV=development

# Database
MONGODB_URI=<mongodb-connection-string>
MONGODB_DB_NAME=yt-downloader

# Redis
REDIS_URI=<redis-connection-string>

# JWT
JWT_PUBLIC_SECRET=<secret>
JWT_PRIVATE_SECRET=<secret>
JWT_PRIVATE_EXPIRATION=31536000

# Firebase (for Google OAuth)
FIREBASE_SERVICE_ACCOUNT_KEY_PATH=./firebase-service-account.json

# YouTube API
YOUTUBE_API_KEY=<api-key>
```

---

## Summary of Changes

### What Was Fixed
1. ✅ Created `/frontend/app/api/public/[...path]/route.ts` to handle public API requests
2. ✅ Added `BACKEND_URL=http://localhost:5000` to `frontend/.env.local`

### What Was Already Working
- `/api/auth/*` routes
- `/api/video/*` routes
- `/api/encode/*` routes
- `/api/download/*` routes (note: may not be actively used)

### Next Steps
1. Restart Next.js development server to load new routes
2. Test public API endpoints (clip, encode, rate-limit)
3. Verify authenticated flows still work as expected
4. Monitor for any remaining 404 errors
