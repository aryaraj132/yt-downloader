# Cookie Handling Verification Report

## ✅ Summary: Cookies Are Properly Handled

Cookies **are correctly passed** from frontend to backend and **are being used** with yt-dlp per-user to distribute rate limits.

---

## Cookie Flow Architecture

### 1. Frontend → API Proxy
**Frontend services** send cookies in the request body:
- `videoService.getAvailableResolutions(url, cookies)` ✅
- `videoService.getAvailableFormats(videoId, cookies)` ✅  
- `videoService.savePublicClip({ cookies, ... })` ✅
- Download preferences include `cookies` field ✅

### 2. API Proxy → Backend
**API Proxy** (`frontend/lib/apiProxy.ts`) forwards all headers and request body:
```typescript
// Line 20-27: Forwards ALL headers (except 'host')
request.headers.forEach((value, key) => {
    if (key.toLowerCase() !== 'host') {
        headers[key] = value;
    }
});

// Line 29-38: Forwards complete request body
const text = await request.text();
body = text || undefined;
```

The proxy passes cookies either as:
- **HTTP Cookie headers** (session cookies)
- **Request body field** (for yt-dlp Netscape format)

### 3. Backend → yt-dlp
**Backend services** extract cookies from request body and pass to yt-dlp:

**Routes that accept cookies:**
- `POST /api/video/download/{videoId}` - Line 294: `cookies = data.get('cookies')`
- `POST /api/video/formats` - Line 494: `cookies = data.get('cookies')`
- `POST /api/public/clip` - Line 57: `cookies = data.get('cookies')`

**Services that use cookies with yt-dlp:**

**`YouTubeService.download_segment()`** (lines 277-285):
```python
if cookies:
    cookies_filename = f"cookies_dl_{uuid.uuid4()}_{int(time.time())}.txt"
    cookies_file = os.path.join(os.getcwd(), cookies_filename)
    
    with open(cookies_file, 'w', encoding='utf-8') as f:
        f.write(cookies)
    
    cmd.extend(['--cookies', cookies_file])
```

**`VideoService.download_video_segment()`** (lines 69-80):
```python
if cookies_content:
    cookies_filename = f"cookies_{uuid.uuid4()}_{int(time.time())}.txt"
    cookies_file = os.path.join(os.path.dirname(output_path), cookies_filename)
    
    with open(cookies_file, 'w', encoding='utf-8') as f:
        f.write(cookies_content)
    
    cmd.extend(['--cookies', cookies_file])
    logger.info(f"Using provided cookies for download: {cookies_file}")
```

**Cleanup:** Cookies files are automatically deleted after use (lines 241-246, 320-324)

---

## Per-User Rate Limit Distribution

### How It Works

1. **Each user's browser** provides their own YouTube cookies
2. **Cookies are unique** per browser/account (different sessions, different rate limits)
3. **Backend passes cookies to yt-dlp** using temporary files
4. **yt-dlp uses those cookies** when making requests to YouTube
5. **YouTube applies rate limits** based on the cookies (per-account basis)

### Result
✅ **Rate limits are distributed per user**, not shared across all users  
✅ **No default cookies** - only user-provided cookies are used  
✅ **Each browser gets its own quota** from YouTube

---

## Cookie Format

**Expected Format:** Netscape HTTP Cookie File format
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	0	CONSENT	YES+1
.youtube.com	TRUE	/	FALSE	1735948800	VISITOR_INFO1_LIVE	...
```

**How users provide cookies:**
- Export from browser using extensions (e.g., "Get cookies.txt")
- Paste into frontend cookie field
- Frontend sends as string in request body
- Backend writes to temp file for yt-dlp

---

## Verification Checklist

- [x] **Frontend** sends cookies in request body
- [x] **API Proxy** forwards request body intact
- [x] **Backend routes** extract cookies from request
- [x] **Backend services** write cookies to temp files
- [x] **yt-dlp** receives cookies via `--cookies` flag
- [x] **Cleanup** removes temp cookie files after use
- [x] **Per-user isolation** - each request uses its own cookies

---

## Security Notes

### ✅ What's Good
- Cookies are stored in **temporary files** with unique UUIDs
- Files are **automatically deleted** after yt-dlp completes
- Cookies are **never logged** (secure handling)
- Each request gets its **own temp file** (no collision risk)

### ⚠️ Recommendations
1. **Encrypt cookie storage** if you add persistent cookie storage in future
2. **Validate cookie format** before passing to yt-dlp (prevent injection)
3. **Rate limit cookie uploads** to prevent abuse
4. **Consider cookie expiry** - inform users when cookies expire

---

## Conclusion

✅ **Cookies are properly passed and used**  
✅ **Each user's browser cookies are isolated**  
✅ **Rate limits are distributed per user, not shared**  
✅ **No default cookies are used (preventing global rate limits)**

The implementation correctly handles per-user cookies to distribute YouTube rate limits across different users/browsers.
