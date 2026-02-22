import { Router, Request, Response } from 'express';
import { Types } from 'mongoose';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { makeId } from '@aryaraj132/corekit-js/utils';
import { Video } from '../models/Video';
import { queueService } from '../services/queueService';
import { progressService } from '../services/progressService';
import { storageService } from '../services/storageService';
import { getRedis } from '../redis';
import { validateYoutubeUrl, validateTimeRange, parseVideoIdFromUrl } from '../utils/validators';
import { config } from '../config';
import { winstonLogger } from '../infra/loggers/winstonLogger';
import crypto from 'crypto';

const router = Router();

const upload = multer({
    dest: os.tmpdir(),
    limits: { fileSize: config.maxUploadSizeMb * 1024 * 1024 },
});

/**
 * Get fingerprint from request for guest rate limiting.
 */
function getFingerprint(req: Request): string {
    const ip = req.ip || req.socket.remoteAddress || 'unknown';
    const fp = req.headers['x-browser-fingerprint'] || '';
    return crypto.createHash('sha256').update(`${ip}:${fp}`).digest('hex').substring(0, 16);
}

/**
 * Check and update rate limit for public API.
 */
async function checkRateLimit(fingerprint: string): Promise<{
    allowed: boolean;
    remaining: number;
    limit: number;
    resetAt: Date;
}> {
    const redis = getRedis();
    const key = `rate_limit:public:${fingerprint}`;
    const limit = config.publicApi.rateLimit;

    // Get current count
    const current = parseInt(await redis.get(key) || '0', 10);

    // Calculate reset time (end of current day UTC)
    const now = new Date();
    const resetAt = new Date(now);
    resetAt.setUTCHours(23, 59, 59, 999);

    if (current >= limit) {
        return { allowed: false, remaining: 0, limit, resetAt };
    }

    // Increment
    await redis.incr(key);
    // Set expiry to end of day if not set
    const ttl = await redis.ttl(key);
    if (ttl < 0) {
        const secondsUntilReset = Math.ceil((resetAt.getTime() - now.getTime()) / 1000);
        await redis.expire(key, secondsUntilReset);
    }

    return { allowed: true, remaining: limit - current - 1, limit, resetAt };
}

// POST /api/public/clip — Public clip endpoint for guests
router.post('/clip', async (req: Request, res: Response) => {
    try {
        const fingerprint = getFingerprint(req);
        const rateLimit = await checkRateLimit(fingerprint);

        if (!rateLimit.allowed) {
            return res.status(429).json({
                error: 'Rate limit exceeded',
                rate_limit: {
                    remaining: rateLimit.remaining,
                    limit: rateLimit.limit,
                    reset_at: rateLimit.resetAt.toISOString(),
                },
            });
        }

        const { url, start_time, end_time, format, resolution } = req.body;

        if (!url || start_time == null || end_time == null) {
            return res.status(400).json({ error: 'Missing required fields: url, start_time, end_time' });
        }

        const [validUrl, urlErr] = validateYoutubeUrl(url);
        if (!validUrl) return res.status(400).json({ error: urlErr });

        const startNum = parseInt(start_time, 10);
        const endNum = parseInt(end_time, 10);
        if (isNaN(startNum) || isNaN(endNum)) {
            return res.status(400).json({ error: 'Invalid time values' });
        }

        const [validTime, timeErr] = validateTimeRange(startNum, endNum, config.publicApi.maxClipDuration);
        if (!validTime) return res.status(400).json({ error: timeErr });

        const youtubeVideoId = parseVideoIdFromUrl(url);

        // Create video entry (no user — guest)
        const video = await Video.create({
            user_id: new Types.ObjectId('000000000000000000000000'), // Guest placeholder
            source_type: 'youtube',
            url,
            youtube_video_id: youtubeVideoId || undefined,
            start_time: startNum,
            end_time: endNum,
            status: 'processing',
            format_preference: format || 'mp4',
            resolution_preference: resolution || 'best',
            job_type: 'download',
        });

        const jobId = await queueService.addDownloadJob({
            video_id: video._id.toString(),
            user_id: '000000000000000000000000',
            url,
            start_time: startNum,
            end_time: endNum,
            format_preference: format || 'mp4',
            resolution_preference: resolution || 'best',
        });

        video.job_id = jobId;
        await video.save();

        res.status(201).json({
            job_id: jobId,
            message: 'Clip job queued',
            status_url: `/api/public/status/${jobId}`,
            download_url: `/api/public/download/${jobId}`,
            rate_limit: {
                remaining: rateLimit.remaining,
                limit: rateLimit.limit,
                reset_at: rateLimit.resetAt.toISOString(),
            },
        });
    } catch (error: any) {
        winstonLogger.error('Public clip error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/public/status/:jobId
router.get('/status/:jobId', async (req: Request, res: Response) => {
    try {
        const { jobId } = req.params;
        const progress = await progressService.getProgress(jobId);

        // Also find the video to get final status
        const video = await Video.findOne({ job_id: jobId }).lean();

        const status = video?.status || progress?.status || 'unknown';
        const fileReady = video?.status === 'completed' && !!video?.file_path;

        res.json({
            job_id: jobId,
            status,
            progress: progress ? parseFloat(String(progress.download_progress || 0)) : 0,
            current_phase: progress?.current_phase || 'initializing',
            file_ready: fileReady,
            error_message: video?.error_message,
        });
    } catch (error: any) {
        winstonLogger.error('Public status error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/public/download/:jobId
router.get('/download/:jobId', async (req: Request, res: Response) => {
    try {
        const { jobId } = req.params;
        const video = await Video.findOne({ job_id: jobId }).lean();

        if (!video) return res.status(404).json({ error: 'Job not found' });
        if (video.status !== 'completed' || !video.file_path) {
            return res.status(400).json({ error: 'File not ready yet' });
        }

        if (video.storage_mode === 's3') {
            const downloadUrl = storageService.getDirectUrl(video.file_path);
            return res.json({ download_url: downloadUrl });
        }

        res.status(404).json({ error: 'File not found' });
    } catch (error: any) {
        winstonLogger.error('Public download error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/public/encode — Public encode endpoint for guests
router.post('/encode', upload.single('video'), async (req: Request, res: Response) => {
    try {
        const fingerprint = getFingerprint(req);
        const rateLimit = await checkRateLimit(fingerprint);

        if (!rateLimit.allowed) {
            return res.status(429).json({
                error: 'Rate limit exceeded',
                rate_limit: {
                    remaining: rateLimit.remaining,
                    limit: rateLimit.limit,
                    reset_at: rateLimit.resetAt.toISOString(),
                },
            });
        }

        if (!req.file) return res.status(400).json({ error: 'No video file provided' });

        const { video_codec = 'h264', quality_preset = 'high' } = req.body;
        const tempPath = req.file.path;

        // Upload to S3
        const s3Key = `${config.s3.keyPrefix}uploads/${makeId(16)}_${Date.now()}_${req.file.originalname}`;
        const [uploadSuccess, uploadResult] = await storageService.uploadFile(tempPath, s3Key);
        try { fs.unlinkSync(tempPath); } catch { /* ignore */ }

        if (!uploadSuccess) {
            return res.status(500).json({ error: `Upload failed: ${uploadResult}` });
        }

        const video = await Video.create({
            user_id: new Types.ObjectId('000000000000000000000000'),
            source_type: 'upload',
            status: 'processing',
            original_filename: req.file.originalname,
            input_file_path: s3Key,
            storage_mode: 's3',
            file_size_bytes: req.file.size,
            video_codec,
            quality_preset,
            job_type: 'encode',
        });

        const jobId = await queueService.addEncodeJob({
            video_id: video._id.toString(),
            user_id: '000000000000000000000000',
            s3_input_key: s3Key,
            original_filename: req.file.originalname,
            video_codec,
            quality_preset,
        });

        video.job_id = jobId;
        await video.save();

        res.status(201).json({
            job_id: jobId,
            message: 'Encoding job queued',
            status_url: `/api/public/status/${jobId}`,
            download_url: `/api/public/download/${jobId}`,
            rate_limit: {
                remaining: rateLimit.remaining,
                limit: rateLimit.limit,
                reset_at: rateLimit.resetAt.toISOString(),
            },
        });
    } catch (error: any) {
        winstonLogger.error('Public encode error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/public/rate-limit
router.get('/rate-limit', async (req: Request, res: Response) => {
    try {
        const fingerprint = getFingerprint(req);
        const redis = getRedis();
        const key = `rate_limit:public:${fingerprint}`;
        const used = parseInt(await redis.get(key) || '0', 10);

        const now = new Date();
        const resetAt = new Date(now);
        resetAt.setUTCHours(23, 59, 59, 999);

        res.json({
            limit: config.publicApi.rateLimit,
            used,
            remaining: Math.max(0, config.publicApi.rateLimit - used),
            reset_at: resetAt.toISOString(),
        });
    } catch (error: any) {
        winstonLogger.error('Public rate limit error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

export default router;
