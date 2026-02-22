/**
 * Validation utility functions ported from Python backend.
 */

const YOUTUBE_URL_PATTERNS = [
    /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]{11}/,
    /^https?:\/\/youtu\.be\/[\w-]{11}/,
    /^https?:\/\/(www\.)?youtube\.com\/live\/[\w-]{11}/,
    /^https?:\/\/(www\.)?youtube\.com\/shorts\/[\w-]{11}/,
];

export function validateYoutubeUrl(url: string): [boolean, string | null] {
    if (!url || typeof url !== 'string') {
        return [false, 'URL is required'];
    }
    const isValid = YOUTUBE_URL_PATTERNS.some((pattern) => pattern.test(url));
    if (!isValid) {
        return [false, 'Invalid YouTube URL format'];
    }
    return [true, null];
}

export function parseVideoIdFromUrl(url: string): string | null {
    // https://youtube.com/watch?v=VIDEO_ID
    let match = url.match(/[?&]v=([\w-]{11})/);
    if (match) return match[1];
    // https://youtu.be/VIDEO_ID
    match = url.match(/youtu\.be\/([\w-]{11})/);
    if (match) return match[1];
    // https://youtube.com/live/VIDEO_ID or /shorts/VIDEO_ID
    match = url.match(/youtube\.com\/(?:live|shorts)\/([\w-]{11})/);
    if (match) return match[1];
    return null;
}

export function validateTimeRange(
    startTime: number,
    endTime: number,
    maxDuration: number
): [boolean, string | null] {
    if (typeof startTime !== 'number' || typeof endTime !== 'number') {
        return [false, 'Start and end times must be numbers'];
    }
    if (startTime < 0) {
        return [false, 'Start time cannot be negative'];
    }
    if (endTime <= startTime) {
        return [false, 'End time must be greater than start time'];
    }
    const duration = endTime - startTime;
    if (duration > maxDuration) {
        return [false, `Duration exceeds maximum of ${maxDuration} seconds`];
    }
    return [true, null];
}

export function validateVideoId(videoId: string): [boolean, string | null] {
    if (!videoId || typeof videoId !== 'string') {
        return [false, 'Video ID is required'];
    }
    if (!/^[\w-]{11}$/.test(videoId)) {
        return [false, 'Invalid YouTube video ID format'];
    }
    return [true, null];
}

export function validateFormatPreference(format: string): [boolean, string | null] {
    const validFormats = ['mp4', 'webm', 'best'];
    if (!validFormats.includes(format)) {
        return [false, `Invalid format. Supported: ${validFormats.join(', ')}`];
    }
    return [true, null];
}

export function validateResolutionPreference(resolution: string): [boolean, string | null] {
    const validResolutions = ['best', 'worst', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p', '4320p'];
    if (!validResolutions.includes(resolution)) {
        return [false, `Invalid resolution. Supported: ${validResolutions.join(', ')}`];
    }
    return [true, null];
}

export function validateEmail(email: string): [boolean, string | null] {
    if (!email || typeof email !== 'string') {
        return [false, 'Email is required'];
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return [false, 'Invalid email format'];
    }
    return [true, null];
}

export function validatePassword(password: string): [boolean, string | null] {
    if (!password || typeof password !== 'string') {
        return [false, 'Password is required'];
    }
    if (password.length < 8) {
        return [false, 'Password must be at least 8 characters'];
    }
    return [true, null];
}
