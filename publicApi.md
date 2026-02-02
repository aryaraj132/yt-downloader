# Public API Implementation Plan

## Goal

Create two public API endpoints accessible without user authentication, with IP-based rate limiting:

1. **Public Video Clipping API** - Download YouTube video segments (max 40 seconds)
2. **Public Video Encoding API** - Encode uploaded videos (max 5 minutes duration)

Both public APIs will share a combined rate limit of **10 operations per day per client** (tracked via IP address + browser fingerprint).

Authenticated users will continue using existing endpoints without these restrictions.

## Rate Limiting Strategy

**Approach**: IP Address + Browser Fingerprint

The rate limiting uses a composite key combining:
- **IP Address** - Extracted from request headers (X-Forwarded-For or direct IP)
- **Browser Fingerprint** - Client-side data including:
  - User-Agent
  - Screen resolution
  - Timezone
  - Language preferences
  - Platform information
  - Canvas fingerprint hash (optional)

**Composite Key Format**: `SHA256(IP + UserAgent + Screen + Timezone + Language)`

This prevents:
- Simple IP changes from bypassing limits
- Cookie/localStorage manipulation
- Basic VPN switching

**Storage**: Redis with daily expiration (resets at midnight UTC)

> [!WARNING]
> **Security Considerations**
> 
> - IP-based rate limiting can be bypassed with VPNs
> - Browser fingerprinting adds additional layer but not foolproof
> - This is designed for incentivizing login, not absolute security
> - Combination of IP + fingerprint makes bypass significantly harder

> [!NOTE]
> **Video Duration Validation**
> 
> - **For downloads**: Validated at request time (start_time - end_time)
> - **For uploads**: Validated client-side before upload using HTML5 File API
> - Backend validates again after upload as final check
> - This prevents unnecessary large file uploads

---

## Proposed Changes

### Backend Components

#### Rate Limiting Service

##### [NEW] [rate_limiter_service.py](file:///d:/yt-downloader/src/services/rate_limiter_service.py)

**Purpose**: Track and enforce IP + browser fingerprint based rate limits for public APIs

**Features**:
- Track operations per composite client identifier (IP + browser fingerprint)
- Combined pool for both clip downloading and encoding (10 per day)
- Store in Redis with daily expiration
- Methods:
  - `create_client_id(ip: str, fingerprint: dict) -> str` - Generate SHA256 composite key
  - `check_rate_limit(client_id: str) -> tuple[bool, int, datetime]` - Returns (allowed, remaining, reset_time)
  - `increment_usage(client_id: str) -> bool` - Increment usage counter
  - `get_remaining(client_id: str) -> int` - Get remaining quota
  - `get_client_info(client_id: str) -> dict` - Get usage details
  - `reset_limit(client_id: str) -> bool` - Admin function to reset

**Implementation Details**:
```python
# Composite ID generation
client_id = SHA256(f"{ip}:{user_agent}:{screen}:{timezone}:{language}")

# Redis key format: rate_limit:public:{client_id}
# Value: JSON with { 
#   "count": 0, 
#   "operations": [{"type": "clip", "timestamp": "..."}],
#   "ip": "...",
#   "fingerprint": {...}
# }
# TTL: Expires at midnight UTC
```

---

#### Validation Service

##### [NEW] [validation_service.py](file:///d:/yt-downloader/src/services/validation_service.py)

**Purpose**: Validate video durations and parameters for public APIs

**Features**:
- Validate video clip duration (max 40 seconds for public)
- Validate uploaded video duration (max 5 minutes for public)
- Extract video metadata using ffprobe
- Methods:
  - `validate_clip_duration(start_time: int, end_time: int, is_public: bool) -> tuple[bool, str]`
  - `validate_upload_duration(file_path: str, is_public: bool) -> tuple[bool, str, float]`
  - `get_video_duration(file_path: str) -> float`

---

#### Middleware

##### [MODIFY] [auth.py](file:///d:/yt-downloader/src/middleware/auth.py#L112-L138)

**Changes**: Add new middleware decorator `require_browser_rate_limit`

**Purpose**: Enforce rate limits for public API endpoints

**Features**:
- Extract IP address from request (handles X-Forwarded-For, X-Real-IP)
- Extract browser fingerprint from request headers (`X-Browser-Fingerprint`)
- Create composite client ID
- Check rate limit before processing request
- Return 429 (Too Many Requests) if limit exceeded
- Attach rate limit info to response headers:
  - `X-RateLimit-Limit: 10`
  - `X-RateLimit-Remaining: 5`
  - `X-RateLimit-Reset: <timestamp>`
- Attach client identification info to `g.client_id` for route access

**Helper Functions**:
```python
def get_client_ip(request) -> str:
    """Extract real client IP from request headers"""
    
def get_browser_fingerprint(request) -> dict:
    """Parse browser fingerprint from headers"""
```

---

#### Routes - Public Video API

##### [NEW] [public_api.py](file:///d:/yt-downloader/src/routes/public_api.py)

**Purpose**: New blueprint for public API endpoints

**Endpoints**:

1. **POST `/api/public/clip`** - Save and download video clip
   - **No authentication required**
   - **Rate limited**: 10/day per client (IP + fingerprint)
   - **Request Headers**:
     - `X-Browser-Fingerprint`: JSON string with browser info
   - **Request Body**:
     ```json
     {
       "url": "https://youtube.com/watch?v=...",
       "start_time": 10,
       "end_time": 45,
       "cookies": "..."
     }
     ```
   - **Validation**:
     - `end_time - start_time <= 40` seconds
     - Valid YouTube URL
   - **Response**:
     ```json
     {
       "video_id": "...",
       "message": "Clip saved, processing...",
       "status_url": "/api/public/clip/status/{video_id}",
       "rate_limit": {
         "remaining": 9,
         "limit": 10,
         "reset_at": "2026-02-03T00:00:00Z"
       }
     }
     ```

2. **POST `/api/public/encode`** - Upload and encode video
   - **No authentication required**
   - **Rate limited**: 10/day per client (shared with clip)
   - **Request Headers**:
     - `X-Browser-Fingerprint`: JSON string with browser info
   - **Form Data**:
     - `video`: File upload
     - `video_codec`: "h264" | "h265" | "av1"
     - `quality_preset`: "lossless" | "high" | "medium"
     - `duration`: Client-provided duration in seconds (for pre-validation)
   - **Validation**:
     - Client-provided duration <= 5 minutes (pre-check)
     - Actual video duration <= 5 minutes (backend validation after upload)
     - Allowed file formats
   - **Response**:
     ```json
     {
       "encode_id": "...",
       "message": "Video uploaded, encoding...",
       "status_url": "/api/public/encode/status/{encode_id}",
       "rate_limit": {
         "remaining": 8,
         "limit": 10,
         "reset_at": "2026-02-03T00:00:00Z"
       }
     }
     ```

3. **GET `/api/public/clip/status/{video_id}`** - Get clip status
   - **No authentication required**
   - **No rate limit** (status checks are free)
   - **Response**: Same as `/api/video/status/{video_id}` but accessible publicly

4. **GET `/api/public/clip/download/{video_id}`** - Download clip
   - **No authentication required**
   - **No rate limit** (downloads are free after creation)
   - **Response**: Video file blob

5. **GET `/api/public/encode/status/{encode_id}`** - Get encoding status
   - **No authentication required**
   - **No rate limit**

6. **GET `/api/public/encode/download/{encode_id}`** - Download encoded video
   - **No authentication required**
   - **No rate limit**

7. **GET `/api/public/rate-limit`** - Check rate limit status
   - **No authentication required**
   - **Request Headers**:
     - `X-Browser-Fingerprint`: JSON string with browser info
   - **Response**:
     ```json
     {
       "limit": 10,
       "used": 3,
       "remaining": 7,
       "reset_at": "2026-02-03T00:00:00Z"
     }
     ```

---

#### Models

##### [MODIFY] [video.py](file:///d:/yt-downloader/src/models/video.py#L22-L81)

**Changes**:
- Add `is_public_api: bool` field to track public vs authenticated requests
- Add `client_info: Optional[dict]` field for public API requests (stores IP + fingerprint hash)
- Update `create_video_info()` to accept these parameters
- Update `create_encode_request()` to accept these parameters

---

#### Configuration

##### [MODIFY] [config.py](file:///d:/yt-downloader/src/config.py#L17-L68)

**Add new configuration variables**:
```python
# Public API Rate Limiting
PUBLIC_API_RATE_LIMIT = int(os.getenv('PUBLIC_API_RATE_LIMIT', 10))  # Operations per day
PUBLIC_API_MAX_CLIP_DURATION = int(os.getenv('PUBLIC_API_MAX_CLIP_DURATION', 40))  # Seconds
PUBLIC_API_MAX_ENCODE_DURATION = int(os.getenv('PUBLIC_API_MAX_ENCODE_DURATION', 300))  # 5 minutes in seconds
```

---

#### Application

##### [MODIFY] [app.py](file:///d:/yt-downloader/src/app.py#L37-L41)

**Changes**: Register new `public_api_bp` blueprint
```python
from src.routes.public_api import public_api_bp
# ...
app.register_blueprint(public_api_bp)
```

---

### Frontend Components

#### API Service

##### [NEW] [browserFingerprint.ts](file:///d:/yt-downloader/frontend/lib/browserFingerprint.ts)

**Purpose**: Generate consistent browser fingerprint for rate limiting

**Implementation**:
```typescript
export interface BrowserFingerprint {
    userAgent: string;
    screen: string;
    timezone: number;
    language: string;
    platform: string;
}

export function getBrowserFingerprint(): BrowserFingerprint {
    if (typeof window === 'undefined') {
        return { userAgent: '', screen: '', timezone: 0, language: '', platform: '' };
    }
    
    return {
        userAgent: navigator.userAgent,
        screen: `${screen.width}x${screen.height}x${screen.colorDepth}`,
        timezone: new Date().getTimezoneOffset(),
        language: navigator.language,
        platform: navigator.platform
    };
}
```

##### [MODIFY] [api.ts](file:///d:/yt-downloader/frontend/lib/api.ts)

**Add public API client** (no authentication):
```typescript
import { getBrowserFingerprint } from './browserFingerprint';

// Create a separate axios instance for public APIs
export const publicApi = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add browser fingerprint to all public requests
publicApi.interceptors.request.use((config) => {
    const fingerprint = getBrowserFingerprint();
    config.headers['X-Browser-Fingerprint'] = JSON.stringify(fingerprint);
    return config;
});
```

---

#### Video Service

##### [MODIFY] [videoService.ts](file:///d:/yt-downloader/frontend/services/videoService.ts)

**Add public API methods**:
```typescript
// Public clip download (no auth)
async savePublicClip(data: {
    url: string;
    start_time: number;
    end_time: number;
    cookies?: string;
}): Promise<{
    video_id: string;
    message: string;
    status_url: string;
    rate_limit: { remaining: number; limit: number; reset_at: string }
}> {
    const response = await publicApi.post('/public/clip', data);
    return response.data;
}

// Public encode (no auth) - with client-side duration check
async encodePublic(file: File, options: {
    video_codec: string;
    quality_preset: string;
}): Promise<{
    encode_id: string;
    message: string;
    status_url: string;
    rate_limit: { remaining: number; limit: number; reset_at: string }
}> {
    // Get video duration client-side
    const duration = await getVideoDuration(file);
    
    const formData = new FormData();
    formData.append('video', file);
    formData.append('video_codec', options.video_codec);
    formData.append('quality_preset', options.quality_preset);
    formData.append('duration', duration.toString());
    
    const response = await publicApi.post('/public/encode', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
}

// Check rate limit
async checkRateLimit(): Promise<{
    limit: number;
    used: number;
    remaining: number;
    reset_at: string;
}> {
    const response = await publicApi.get('/public/rate-limit');
    return response.data;
}

// Helper: Get video duration from File using HTML5
async function getVideoDuration(file: File): Promise<number> {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        video.preload = 'metadata';
        
        video.onloadedmetadata = () => {
            window.URL.revokeObjectURL(video.src);
            resolve(video.duration);
        };
        
        video.onerror = () => {
            reject(new Error('Failed to load video metadata'));
        };
        
        video.src = URL.createObjectURL(file);
    });
}
}
```

---

#### Encode Service

##### [MODIFY] [encodeService.ts](file:///d:/yt-downloader/frontend/services/encodeService.ts)

**Add public encoding methods** similar to videoService

---

#### UI Components

##### [MODIFY] [download/page.tsx](file:///d:/yt-downloader/frontend/app/download/page.tsx)

**Changes**:
- Add toggle/tab for "Guest Mode" vs "Signed In Mode"
- Show rate limit info for guest users
- Display remaining quota prominently
- Show upgrade prompt when limit reached
- Enforce 40-second max duration for guest users

##### [MODIFY] [encode/page.tsx](file:///d:/yt-downloader/frontend/app/encode/page.tsx)

**Changes**:
- Add toggle/tab for "Guest Mode" vs "Signed In Mode"
- Show rate limit info for guest users
- Validate file duration before/after upload for guests
- Show 5-minute limit warning
- Show upgrade prompt when limit reached

---

## Verification Plan

### Automated Tests

#### 1. Rate Limiting Service Tests

**File**: Create `tests/test_rate_limiter_service.py`

**Test Cases**:
- Test rate limit initialization
- Test increment and decrement
- Test daily reset (using mock time)
- Test concurrent requests
- Test Redis persistence

**Run Command**:
```bash
pytest tests/test_rate_limiter_service.py -v
```

#### 2. Public API Endpoint Tests

**File**: Create `tests/test_public_api.py`

**Test Cases**:
- Test `/api/public/clip` with valid data
- Test clip duration validation (reject > 40s)
- Test rate limiting (11th request should fail)
- Test `/api/public/encode` with valid video
- Test encode duration validation (reject > 5min)
- Test rate limit sharing between clip and encode
- Test status and download endpoints
- Test browser ID requirement

**Run Command**:
```bash
pytest tests/test_public_api.py -v
```

#### 3. Integration Tests

**File**: `tests/test_public_api_integration.py`

**Test Cases**:
- Complete flow: clip save → status check → download
- Complete flow: upload → encode → status check → download
- Rate limit enforcement across both APIs
- Redis key expiration

**Run Command**:
```bash
pytest tests/test_public_api_integration.py -v
```

### Manual Verification

#### 1. Public Clip Download Flow

**Prerequisites**:
- Backend server running: `python start_server.py`
- Frontend server running: `cd frontend && npm run dev`
- Open browser at `http://localhost:3000/download`

**Steps**:
1. **Log out** if currently logged in
2. Toggle to "Guest Mode"
3. Verify rate limit shows "10 remaining"
4. Enter YouTube URL and set 30-second clip
5. Click "Download Clip"
6. Verify:
   - ✅ Rate limit decrements to "9 remaining"
   - ✅ Status polling works
   - ✅ Download completes
7. Repeat 9 more times
8. On 11th attempt, verify:
   - ✅ Shows error: "Daily limit reached"
   - ✅ Displays upgrade prompt
9. Click "Sign In" and log in
10. Verify:
    - ✅ Can download clips without limit
    - ✅ Can download clips > 40 seconds

#### 2. Public Encode Flow

**Steps**:
1. Open `http://localhost:3000/encode` in guest mode
2. Upload a 2-minute video
3. Select codec and quality
4. Click "Encode"
5. Verify:
   - ✅ Encoding starts (rate limit should reflect shared pool)
   - ✅ Status updates work
   - ✅ Download works after completion
6. Try uploading a 10-minute video
7. Verify:
   - ✅ Rejected with "Video too long" error
8. Sign in and repeat with 10-minute video
9. Verify:
   - ✅ Accepted and encoded successfully

#### 3. Rate Limit Persistence

**Steps**:
1. Use guest mode, perform 5 operations
2. Note current IP and browser info
3. Close browser
4. Reopen browser (same IP, same browser)
5. Return to download page
6. Verify:
   - ✅ Rate limit shows "5 remaining" (persisted via IP + fingerprint)
7. Change browser (different User-Agent)
8. Verify:
   - ✅ Rate limit resets to "10 remaining" (different fingerprint)
9. Use VPN to change IP
10. Verify:
    - ✅ Rate limit resets to "10 remaining" (different IP)

#### 4. Cross-API Rate Limiting

**Steps**:
1. Guest mode: Download 5 clips
2. Verify: "5 remaining"
3. Encode 3 videos
4. Verify: "2 remaining"
5. Try downloading 1 clip and encoding 1 video
6. Verify: "0 remaining"
7. Try any operation
8. Verify: ✅ Blocked with limit reached message

### Performance Testing

#### Load Test Public APIs

**Tool**: Use `locust` or `k6` for load testing

**Scenarios**:
1. 100 concurrent users hitting public clip API
2. Verify rate limiting works correctly
3. Check Redis performance under load
4. Ensure no race conditions in rate counter

**Command** (if using existing test infrastructure):
```bash
# To be determined based on existing test setup
locust -f tests/load/test_public_api.py
```

---

## Environment Variables

Add to `.env.example` and deployment documentation:

```bash
# Public API Configuration
PUBLIC_API_RATE_LIMIT=10
PUBLIC_API_MAX_CLIP_DURATION=40
PUBLIC_API_MAX_ENCODE_DURATION=300
```

---

## Database Changes

### MongoDB Collection

No schema changes needed, but existing `videos` collection will include new fields:
- `is_public_api`: boolean
- `client_info`: object (nullable) - Stores `{ "client_id": "hash", "ip": "...", "fingerprint": {...} }`

### Redis Keys

New key patterns:
- `rate_limit:public:{client_id}` - Rate limit tracking
  - `client_id` = SHA256(IP + UserAgent + Screen + Timezone + Language)
  - Structure: `{ "count": 5, "operations": [...], "ip": "...", "fingerprint": {...} }`
  - TTL: Until midnight UTC

---

## Migration Steps

1. Deploy backend changes (services, routes, middleware)
2. Run database migration (if needed)
3. Test public APIs with Postman/curl
4. Deploy frontend changes
5. Test end-to-end flows
6. Monitor Redis and rate limiting behavior
7. Gather user feedback

---

## Rollback Plan

If issues arise:
1. Remove `public_api_bp` registration from `app.py`
2. Revert frontend to show only authenticated mode
3. Clear Redis rate limit keys: `redis-cli KEYS "rate_limit:public:*" | xargs redis-cli DEL`

---

## Documentation Updates

Files to update:
- [`README.md`](file:///d:/yt-downloader/README.md) - Document public API endpoints
- [`QUICKSTART.md`](file:///d:/yt-downloader/QUICKSTART.md) - Add public API examples
- [`backend.md`](file:///d:/yt-downloader/backend.md) - API reference for public endpoints
- [`ENVIRONMENT_VARIABLES.md`](file:///d:/yt-downloader/ENVIRONMENT_VARIABLES.md) - New env vars

---

## Future Enhancements

Potential improvements after initial rollout:
- IP-based rate limiting as backup
- Captcha for guest users approaching limit
- Premium tiers with higher limits
- Analytics dashboard for public API usage
- Webhook notifications for completed jobs
