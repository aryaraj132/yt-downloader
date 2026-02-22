import { getRedis } from '../redis';
import { config } from '../config';
import { makeId } from '@aryaraj132/corekit-js/utils';
import { winstonLogger } from '../infra/loggers/winstonLogger';

export interface DownloadJobPayload {
    job_id: string;
    video_id: string;
    user_id: string;
    url: string;
    start_time: number;
    end_time: number;
    format_preference: string;
    resolution_preference: string;
}

export interface EncodeJobPayload {
    job_id: string;
    video_id: string;
    user_id: string;
    s3_input_key: string; // S3 key for uploaded file
    original_filename: string;
    video_codec: string;
    quality_preset: string;
}

/**
 * Service for adding jobs to Redis queues.
 * Uses RPUSH to add to the end of a list. Worker uses BLPOP from the left (FIFO).
 */
export const queueService = {
    /**
     * Add a download job to the queue.
     */
    async addDownloadJob(payload: Omit<DownloadJobPayload, 'job_id'>): Promise<string> {
        const redis = getRedis();
        const jobId = makeId(32);
        const job: DownloadJobPayload = { ...payload, job_id: jobId };

        await redis.rpush(config.queues.download, JSON.stringify(job));

        // Initialize progress tracking
        await redis.hset(`job:${jobId}:progress`, {
            status: 'queued',
            current_phase: 'queued',
            download_progress: '0',
            encoding_progress: '0',
        });
        await redis.expire(`job:${jobId}:progress`, 86400); // 24h TTL

        winstonLogger.info(`Download job queued: ${jobId} for video ${payload.video_id}`);
        return jobId;
    },

    /**
     * Add an encoding job to the queue.
     */
    async addEncodeJob(payload: Omit<EncodeJobPayload, 'job_id'>): Promise<string> {
        const redis = getRedis();
        const jobId = makeId(32);
        const job: EncodeJobPayload = { ...payload, job_id: jobId };

        await redis.rpush(config.queues.encode, JSON.stringify(job));

        // Initialize progress tracking
        await redis.hset(`job:${jobId}:progress`, {
            status: 'queued',
            current_phase: 'queued',
            download_progress: '0',
            encoding_progress: '0',
        });
        await redis.expire(`job:${jobId}:progress`, 86400); // 24h TTL

        winstonLogger.info(`Encode job queued: ${jobId} for video ${payload.video_id}`);
        return jobId;
    },
};
