# How to Get YouTube Cookies for yt-dlp

This guide explains how to obtain a YouTube cookies file and configure it for the worker to use.

## Why Cookies?

YouTube may rate-limit or block downloads from yt-dlp, especially on server IPs. Using cookies from a logged-in browser session can help bypass these restrictions by authenticating as a real user.

## Cookie File Name

The worker expects the cookie file at:
```
worker/cookiesFile/cookies.txt
```

**The file MUST be named `cookies.txt`** — this is the exact filename the worker looks for.

## How to Get the Cookies File

### Method 1: Browser Extension (Recommended)

1. Install a cookie export extension:
   - **Chrome**: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - **Firefox**: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. Go to [youtube.com](https://youtube.com) and make sure you're **logged in**

3. Click the extension icon and export/download the cookies

4. Save the file as `cookies.txt` in the `worker/cookiesFile/` directory

### Method 2: Using yt-dlp Directly

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt https://www.youtube.com
```

This extracts cookies from your Chrome browser and saves them to `cookies.txt`. Move this file to `worker/cookiesFile/cookies.txt`.

Supported browsers: `chrome`, `firefox`, `edge`, `opera`, `brave`, `vivaldi`, `safari`

### Method 3: Manual (Netscape Format)

The cookies file must be in **Netscape/Mozilla cookie format**. Each line contains tab-separated fields:

```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	0	VISITOR_INFO1_LIVE	value_here
.youtube.com	TRUE	/	TRUE	0	YSC	value_here
.youtube.com	TRUE	/	TRUE	0	PREF	value_here
.youtube.com	TRUE	/	TRUE	0	LOGIN_INFO	value_here
.youtube.com	TRUE	/	TRUE	0	SID	value_here
.youtube.com	TRUE	/	TRUE	0	HSID	value_here
.youtube.com	TRUE	/	TRUE	0	SSID	value_here
.youtube.com	TRUE	/	TRUE	0	APISID	value_here
.youtube.com	TRUE	/	TRUE	0	SAPISID	value_here
```

## Important Notes

- **Cookie files expire** — YouTube cookies typically last a few weeks to months. If downloads start failing with 429 errors, **replace the cookies file** with a fresh one.
- **One account per file** — Use a single Google account's cookies per file.
- **Don't share cookies** — Cookies contain your login session; treat them like passwords.
- **Auto-detection** — The worker automatically detects if `cookies.txt` is present. If the file doesn't exist, yt-dlp runs without cookies (default behavior).
- **No restart needed** — The worker checks for the cookies file on each download job. You can add or replace the file without restarting the worker.

## Verifying Cookies Work

Check the worker logs after submitting a download. You should see:
```
[Download] Using cookies from /app/cookiesFile/cookies.txt
```

If cookies are not detected:
```
No cookie file found, using default yt-dlp behavior
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 429 Too Many Requests | Replace `cookies.txt` with fresh cookies |
| "Sign in to confirm you're not a bot" | Export cookies from a browser where you're logged in |
| Cookies file not detected | Ensure filename is exactly `cookies.txt` (case-sensitive) |
| Downloads still fail | Try cookies from a different Google account |
| Invalid cookie format | Make sure it's Netscape format (use a browser extension) |
