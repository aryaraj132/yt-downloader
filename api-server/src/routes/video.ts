import { Router, Request, Response } from 'express';
import { Types } from 'mongoose';
import { Video } from '../models/Video';
import { User } from '../models/User';
import { requirePrivateToken, requirePublicToken } from '../middleware/auth';
import { queueService } from '../services/queueService';
import { storageService } from '../services/storageService';
import { progressService } from '../services/progressService';
import {
    validateYoutubeUrl,
    validateTimeRange,
    validateVideoId,
    validateFormatPreference,
    validateResolutionPreference,
    parseVideoIdFromUrl,
} from '../utils/validators';
import { config } from '../config';
import { winstonLogger } from '../infra/loggers/winstonLogger';

const router = Router();

// POST /api/video/save
router.post('/save', requirePublicToken, async (req: Request, res: Response) => {
    try {
        const { url, start_time, end_time, user_id, additional_message, clip_offset } = req.body;

        if (!url || start_time == null || end_time == null || !user_id) {
            return res.status(400).json({ error: 'Missing required fields: url, start_time, end_time, user_id' });
        }

        const [validUrl, urlErr] = validateYoutubeUrl(url);
        if (!validUrl) return res.status(400).json({ error: urlErr });

        const startNum = parseInt(start_time, 10);
        const endNum = parseInt(end_time, 10);
        if (isNaN(startNum) || isNaN(endNum)) {
            return res.status(400).json({ error: 'Invalid time values' });
        }

        const [validTime, timeErr] = validateTimeRange(startNum, endNum, config.maxVideoDuration);
        if (!validTime) return res.status(400).json({ error: timeErr });

        const youtubeVideoId = parseVideoIdFromUrl(url);

        const video = await Video.create({
            user_id: new Types.ObjectId(user_id),
            source_type: 'youtube',
            url,
            youtube_video_id: youtubeVideoId || undefined,
            start_time: startNum,
            end_time: endNum,
            status: 'pending',
            additional_message,
            clip_offset: clip_offset ? parseInt(clip_offset, 10) : undefined,
            job_type: 'download',
        });

        winstonLogger.info(`Video info saved: ${video._id}`);

        res.status(201).json({
            message: 'Video info saved successfully',
            video_id: video._id.toString(),
        });
    } catch (error: any) {
        winstonLogger.error('Video save error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/video/download/:videoId — Queue a download job
router.post('/download/:videoId', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { videoId } = req.params;
        const data = req.body || {};
        const formatPref = data.format_preference || config.defaultVideoFormat;
        const resolutionPref = data.resolution_preference || config.defaultVideoResolution;

        // Validate preferences
        if (formatPref !== config.defaultVideoFormat) {
            const [valid, err] = validateFormatPreference(formatPref);
            if (!valid) return res.status(400).json({ error: err });
        }
        if (resolutionPref !== config.defaultVideoResolution) {
            const [valid, err] = validateResolutionPreference(resolutionPref);
            if (!valid) return res.status(400).json({ error: err });
        }

        const video = await Video.findById(videoId);
        if (!video) return res.status(404).json({ error: 'Video not found' });

        // Verify ownership
        if (video.user_id.toString() !== req.userId) {
            return res.status(403).json({ error: 'Unauthorized access to video' });
        }

        // If already completed and file exists, return the download URL directly
        if (video.status === 'completed' && video.file_path) {
            if (video.storage_mode === 's3') {
                const downloadUrl = storageService.getDirectUrl(video.file_path);
                return res.json({
                    message: 'Download link generated',
                    download_url: downloadUrl,
                    status: 'completed',
                });
            }
        }

        // If already processing, return current status
        if (video.status === 'processing') {
            const progress = video.job_id
                ? await progressService.getProgress(video.job_id)
                : await progressService.getVideoProgress(videoId);

            return res.status(202).json({
                message: 'Video is currently being processed',
                status: 'processing',
                job_id: video.job_id,
                progress,
            });
        }

        // If failed, allow retry
        if (video.status === 'failed') {
            // Reset status to pending for retry
            video.status = 'pending';
            video.error_message = undefined;
        }

        // Queue the download job
        const jobId = await queueService.addDownloadJob({
            video_id: videoId,
            user_id: req.userId!,
            url: video.url!,
            start_time: video.start_time!,
            end_time: video.end_time!,
            format_preference: formatPref,
            resolution_preference: resolutionPref,
        });

        // Update video record
        video.status = 'processing';
        video.job_id = jobId;
        video.format_preference = formatPref;
        video.resolution_preference = resolutionPref;
        await video.save();

        res.json({
            message: 'Download job queued',
            job_id: jobId,
            video_id: videoId,
            status: 'processing',
        });
    } catch (error: any) {
        winstonLogger.error('Video download error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/video/status/:videoId
router.get('/status/:videoId', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { videoId } = req.params;
        const video = await Video.findById(videoId);

        if (!video) return res.status(404).json({ error: 'Video not found' });

        if (video.user_id.toString() !== req.userId) {
            return res.status(403).json({ error: 'Unauthorized access to video' });
        }

        const fileAvailable = video.status === 'completed' && !!video.file_path;

        const response: any = {
            video_id: videoId,
            status: video.status,
            url: video.url,
            start_time: video.start_time,
            end_time: video.end_time,
            created_at: video.created_at.toISOString(),
            file_available: fileAvailable,
            error_message: video.error_message,
            available_formats: video.available_formats,
            job_id: video.job_id,
        };

        // Add download URL if completed
        if (fileAvailable && video.storage_mode === 's3' && video.file_path) {
            response.download_url = storageService.getDirectUrl(video.file_path);
        }

        // Add progress if processing
        if (video.status === 'processing') {
            let progress = null;
            if (video.job_id) {
                progress = await progressService.getProgress(video.job_id);
            }
            if (!progress) {
                progress = await progressService.getVideoProgress(videoId);
            }

            response.progress = progress || { current_phase: 'initializing' };
        }

        res.json(response);
    } catch (error: any) {
        winstonLogger.error('Video status error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/video/list
router.get('/list', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const page = Math.max(1, parseInt(req.query.page as string, 10) || 1);
        const limit = Math.min(100, Math.max(1, parseInt(req.query.limit as string, 10) || 20));
        const skip = (page - 1) * limit;

        const userId = new Types.ObjectId(req.userId);

        const total = await Video.countDocuments({ user_id: userId });
        const videos = await Video.find({ user_id: userId })
            .sort({ created_at: -1 })
            .skip(skip)
            .limit(limit)
            .lean();

        const user = await User.findById(req.userId).select('email').lean();
        const clipperName = user?.email || 'Unknown';

        const videoList = videos.map((video) => {
            const fileAvailable = video.status === 'completed' && !!video.file_path;
            return {
                video_id: video._id.toString(),
                url: video.url,
                start_time: video.start_time,
                end_time: video.end_time,
                status: video.status,
                created_at: video.created_at.toISOString(),
                file_available: fileAvailable,
                youtube_video_id: video.youtube_video_id,
                clipped_by: clipperName,
                download_url: fileAvailable && video.storage_mode === 's3' && video.file_path
                    ? storageService.getDirectUrl(video.file_path)
                    : undefined,
            };
        });

        res.json({
            videos: videoList,
            pagination: {
                page,
                limit,
                total,
                has_more: skip + limit < total,
            },
        });
    } catch (error: any) {
        winstonLogger.error('Video list error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/video/formats
router.post('/formats', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { video_id } = req.body || {};
        if (!video_id) return res.status(400).json({ error: 'Video ID is required' });

        // Check if it's a DB document ID
        const video = await Video.findById(video_id).lean();
        if (video) {
            if (video.user_id.toString() !== req.userId) {
                return res.status(403).json({ error: 'Unauthorized access to video' });
            }
            // Return stored formats if available
            if (video.available_formats) {
                return res.json({
                    video_id: video.youtube_video_id || video_id,
                    resolutions: video.available_formats,
                    extensions: ['mp4', 'webm'],
                    formats: {},
                });
            }
        }

        // For format detection, this requires yt-dlp which runs on the worker.
        // Return a placeholder response — full format detection will happen on download.
        res.json({
            video_id,
            resolutions: ['best', '2160p', '1440p', '1080p', '720p'],
            extensions: ['mp4', 'webm'],
            formats: {},
            note: 'Available formats will be confirmed during download',
        });
    } catch (error: any) {
        winstonLogger.error('Video formats error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/video/formats/:videoId (legacy support)
router.get('/formats/:videoId', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { videoId } = req.params;
        const video = await Video.findById(videoId).lean();

        if (video) {
            if (video.user_id.toString() !== req.userId) {
                return res.status(403).json({ error: 'Unauthorized access to video' });
            }
            if (video.available_formats) {
                return res.json({
                    video_id: video.youtube_video_id || videoId,
                    resolutions: video.available_formats,
                    extensions: ['mp4', 'webm'],
                    formats: {},
                });
            }
        }

        res.json({
            video_id: videoId,
            resolutions: ['best', '2160p', '1440p', '1080p', '720p'],
            extensions: ['mp4', 'webm'],
            formats: {},
        });
    } catch (error: any) {
        winstonLogger.error('Video formats error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/video/resolutions
router.post('/resolutions', async (req: Request, res: Response) => {
    try {
        const { url } = req.body || {};
        if (!url) return res.status(400).json({ error: 'URL is required' });

        const [validUrl, urlErr] = validateYoutubeUrl(url);
        if (!validUrl) return res.status(400).json({ error: urlErr });

        const videoId = parseVideoIdFromUrl(url);
        if (!videoId) return res.status(400).json({ error: 'Could not extract YouTube video ID' });

        // Without yt-dlp on the API server, return default resolutions
        // The worker will handle actual format detection during download
        res.json({
            video_id: videoId,
            url,
            resolutions: ['best', '2160p', '1440p', '1080p', '720p'],
        });
    } catch (error: any) {
        winstonLogger.error('Video resolutions error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/video/debug/connectivity
router.get('/debug/connectivity', async (_req: Request, res: Response) => {
    res.json({
        service: 'api-server',
        message: 'API server does not have yt-dlp. Use worker health check for download connectivity.',
        status: 'healthy',
    });
});

export default router;
