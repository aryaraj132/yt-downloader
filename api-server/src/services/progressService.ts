import { getRedis } from '../redis';
import { winstonLogger } from '../infra/loggers/winstonLogger';

export interface JobProgress {
    status?: string;
    current_phase?: string;
    download_progress?: number;
    encoding_progress?: number;
    speed?: string;
    eta?: string;
    fps?: number;
    error_message?: string;
}

/**
 * Service for reading job progress from Redis.
 * The worker writes progress to `job:{jobId}:progress` Redis hash.
 * The API server only reads from it.
 */
export const progressService = {
    async getProgress(jobId: string): Promise<JobProgress | null> {
        try {
            const redis = getRedis();
            const data = await redis.hgetall(`job:${jobId}:progress`);

            if (!data || Object.keys(data).length === 0) {
                return null;
            }

            const result: JobProgress = {};
            for (const [key, value] of Object.entries(data)) {
                if (key === 'download_progress' || key === 'encoding_progress' || key === 'fps') {
                    result[key as keyof JobProgress] = parseFloat(value) as any;
                } else {
                    (result as any)[key] = value;
                }
            }

            return result;
        } catch (error) {
            winstonLogger.error(`Failed to get progress for job ${jobId}`, '', error);
            return null;
        }
    },

    /**
     * Also support the legacy key format for backward compat with existing frontend polling.
     * The old Python backend used `video:progress:{videoId}` — we also check that.
     */
    async getVideoProgress(videoId: string): Promise<JobProgress | null> {
        try {
            const redis = getRedis();
            const data = await redis.hgetall(`video:progress:${videoId}`);

            if (!data || Object.keys(data).length === 0) {
                return null;
            }

            const result: JobProgress = {};
            for (const [key, value] of Object.entries(data)) {
                if (key === 'download_progress' || key === 'encoding_progress' || key === 'fps') {
                    result[key as keyof JobProgress] = parseFloat(value) as any;
                } else {
                    (result as any)[key] = value;
                }
            }

            return result;
        } catch (error) {
            winstonLogger.error(`Failed to get video progress for ${videoId}`, '', error);
            return null;
        }
    },
};
