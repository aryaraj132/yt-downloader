import { Router, Request, Response } from 'express';
import { Types } from 'mongoose';
import { Video } from '../models/Video';
import { requirePrivateToken } from '../middleware/auth';
import { storageService } from '../services/storageService';
import { winstonLogger } from '../infra/loggers/winstonLogger';

const router = Router();

/**
 * GET /api/jobs/recent
 * Download Center API — returns all jobs from the past 24 hours for the authenticated user.
 */
router.get('/recent', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const userId = new Types.ObjectId(req.userId);
        const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

        const videos = await Video.find({
            user_id: userId,
            created_at: { $gte: twentyFourHoursAgo },
        })
            .sort({ created_at: -1 })
            .lean();

        const jobs = videos.map((video) => {
            const fileAvailable = video.status === 'completed' && !!video.file_path;
            let downloadUrl: string | undefined;

            if (fileAvailable && video.storage_mode === 's3' && video.file_path) {
                downloadUrl = storageService.getDirectUrl(video.file_path);
            }

            return {
                job_id: video.job_id || video._id.toString(),
                video_id: video._id.toString(),
                job_type: video.job_type || (video.source_type === 'upload' ? 'encode' : 'download'),
                status: video.status,
                created_at: video.created_at.toISOString(),
                updated_at: video.updated_at?.toISOString(),
                completed_at: video.encoding_completed_at?.toISOString(),

                // Source info
                url: video.url,
                youtube_video_id: video.youtube_video_id,
                original_filename: video.original_filename,

                // Time range (for downloads)
                start_time: video.start_time,
                end_time: video.end_time,

                // Encoding info
                video_codec: video.video_codec,
                quality_preset: video.quality_preset,

                // Result
                file_available: fileAvailable,
                download_url: downloadUrl,
                file_size_bytes: video.file_size_bytes,
                error_message: video.error_message,
            };
        });

        res.json({
            jobs,
            count: jobs.length,
            period: '24h',
        });
    } catch (error: any) {
        winstonLogger.error('Jobs recent error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

export default router;
