import { Router, Request, Response } from 'express';
import { Types } from 'mongoose';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { makeId } from '@aryaraj132/corekit-js/utils';
import { Video } from '../models/Video';
import { requirePrivateToken } from '../middleware/auth';
import { queueService } from '../services/queueService';
import { progressService } from '../services/progressService';
import { storageService } from '../services/storageService';
import { config } from '../config';
import { winstonLogger } from '../infra/loggers/winstonLogger';

const router = Router();

// Multer config for file uploads
const upload = multer({
    dest: os.tmpdir(),
    limits: { fileSize: config.maxUploadSizeMb * 1024 * 1024 },
    fileFilter: (_req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase().slice(1);
        if (config.allowedVideoFormats.includes(ext)) {
            cb(null, true);
        } else {
            cb(new Error(`Invalid file format. Allowed: ${config.allowedVideoFormats.join(', ')}`));
        }
    },
});

// POST /api/encode/upload — Upload video file to S3 for encoding
router.post('/upload', requirePrivateToken, upload.single('video'), async (req: Request, res: Response) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No video file provided' });
        }

        const originalFilename = req.file.originalname;
        const fileSizeBytes = req.file.size;
        const tempPath = req.file.path;

        // Upload to S3 (worker will download from S3 to encode)
        const s3Key = `${config.s3.keyPrefix}uploads/${makeId(16)}_${Date.now()}_${originalFilename}`;
        const [uploadSuccess, uploadResult] = await storageService.uploadFile(tempPath, s3Key);

        // Clean up temp file
        try { fs.unlinkSync(tempPath); } catch { /* ignore */ }

        if (!uploadSuccess) {
            return res.status(500).json({ error: `Upload failed: ${uploadResult}` });
        }

        // Create encode request in database
        const video = await Video.create({
            user_id: new Types.ObjectId(req.userId),
            source_type: 'upload',
            status: 'pending',
            original_filename: originalFilename,
            input_file_path: s3Key, // Now stores S3 key instead of local path
            storage_mode: 's3',
            file_size_bytes: fileSizeBytes,
            job_type: 'encode',
        });

        winstonLogger.info(`Encode upload created: ${video._id}`);

        res.status(201).json({
            message: 'Video uploaded successfully',
            encode_id: video._id.toString(),
            original_filename: originalFilename,
            file_size_mb: Math.round((fileSizeBytes / (1024 * 1024)) * 100) / 100,
        });
    } catch (error: any) {
        winstonLogger.error('Encode upload error', error.message, error);
        if (error.message?.includes('Invalid file format')) {
            return res.status(400).json({ error: error.message });
        }
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/encode/start/:encodeId — Queue encoding job
router.post('/start/:encodeId', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { encodeId } = req.params;
        const { video_codec = 'h264', quality_preset = 'high' } = req.body || {};

        // Validate codec
        const supportedCodecs: Record<string, string[]> = {
            h264: ['lossless', 'high', 'medium'],
            h265: ['lossless', 'high', 'medium'],
            av1: ['lossless', 'high', 'medium'],
        };

        if (!supportedCodecs[video_codec]) {
            return res.status(400).json({
                error: `Invalid codec. Supported: ${Object.keys(supportedCodecs).join(', ')}`,
            });
        }

        if (!supportedCodecs[video_codec].includes(quality_preset)) {
            return res.status(400).json({
                error: `Invalid quality preset. Supported: ${supportedCodecs[video_codec].join(', ')}`,
            });
        }

        const video = await Video.findById(encodeId);
        if (!video) return res.status(404).json({ error: 'Encode request not found' });

        if (video.user_id.toString() !== req.userId) {
            return res.status(403).json({ error: 'Unauthorized access to encode request' });
        }

        if (video.status === 'processing') {
            return res.status(202).json({ message: 'Video is currently being encoded', status: 'processing' });
        }

        if (video.status === 'completed') {
            return res.json({ message: 'Video already encoded', status: 'completed' });
        }

        // Queue encode job
        const jobId = await queueService.addEncodeJob({
            video_id: encodeId,
            user_id: req.userId!,
            s3_input_key: video.input_file_path!,
            original_filename: video.original_filename || 'video',
            video_codec,
            quality_preset,
        });

        // Update video record
        video.status = 'processing';
        video.job_id = jobId;
        video.video_codec = video_codec;
        video.quality_preset = quality_preset;
        video.encoding_started_at = new Date();
        await video.save();

        res.json({
            message: 'Encoding job queued',
            job_id: jobId,
            encode_id: encodeId,
            status: 'processing',
        });
    } catch (error: any) {
        winstonLogger.error('Encode start error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/encode/status/:encodeId
router.get('/status/:encodeId', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { encodeId } = req.params;
        const video = await Video.findById(encodeId);

        if (!video) return res.status(404).json({ error: 'Encode request not found' });

        if (video.user_id.toString() !== req.userId) {
            return res.status(403).json({ error: 'Unauthorized access to encode request' });
        }

        const fileAvailable = video.status === 'completed' && !!video.file_path;

        const response: any = {
            encode_id: encodeId,
            status: video.status,
            original_filename: video.original_filename,
            video_codec: video.video_codec,
            quality_preset: video.quality_preset,
            created_at: video.created_at.toISOString(),
            file_available: fileAvailable,
            job_id: video.job_id,
        };

        if (fileAvailable && video.storage_mode === 's3' && video.file_path) {
            response.download_url = storageService.getDirectUrl(video.file_path);
        }

        if (video.file_size_bytes) {
            response.file_size_mb = Math.round((video.file_size_bytes / (1024 * 1024)) * 100) / 100;
        }
        if (video.error_message) response.error_message = video.error_message;
        if (video.encoding_started_at) response.encoding_started_at = video.encoding_started_at.toISOString();
        if (video.encoding_completed_at) {
            response.encoding_completed_at = video.encoding_completed_at.toISOString();
            const durationMs = video.encoding_completed_at.getTime() - video.encoding_started_at!.getTime();
            response.encoding_duration_seconds = Math.round(durationMs / 1000);
        }

        // Progress from Redis
        if (video.status === 'processing') {
            let progress = null;
            if (video.job_id) {
                progress = await progressService.getProgress(video.job_id);
            }
            response.progress = progress || { current_phase: 'initializing', encoding_progress: 0 };
        }

        res.json(response);
    } catch (error: any) {
        winstonLogger.error('Encode status error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/encode/download/:encodeId
router.post('/download/:encodeId', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { encodeId } = req.params;
        const video = await Video.findById(encodeId);

        if (!video) return res.status(404).json({ error: 'Encode request not found' });

        if (video.user_id.toString() !== req.userId) {
            return res.status(403).json({ error: 'Unauthorized access to encode request' });
        }

        if (video.status === 'processing') {
            return res.status(202).json({ message: 'Video is still being encoded' });
        }

        if (video.status === 'failed') {
            return res.status(500).json({ error: 'Encoding failed', message: video.error_message });
        }

        if (video.status !== 'completed' || !video.file_path) {
            return res.status(400).json({ error: 'Video not yet encoded' });
        }

        if (video.storage_mode === 's3') {
            const downloadUrl = storageService.getDirectUrl(video.file_path);
            return res.json({ message: 'Download link generated', download_url: downloadUrl });
        }

        res.status(404).json({ error: 'Encoded file not found' });
    } catch (error: any) {
        winstonLogger.error('Encode download error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/encode/codecs
router.get('/codecs', async (_req: Request, res: Response) => {
    res.json({
        codecs: {
            h264: ['lossless', 'high', 'medium'],
            h265: ['lossless', 'high', 'medium'],
            av1: ['lossless', 'high', 'medium'],
        },
    });
});

export default router;
