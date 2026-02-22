/**
 * Application configuration.
 * Follows the same pattern as app-backend/api/config.js — grouped by service.
 */
import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const queuePrefix = process.env.QUEUE_PREFIX ? `${process.env.QUEUE_PREFIX}-` : '';

const config = {
    // Identity
    containerAppName: 'yt-downloader-api',
    containerId: `${queuePrefix}yt-downloader-api`,
    serviceName: 'yt-downloader-api',
    environment: process.env.NODE_ENV || 'development',
    isDebug: ['local', 'development', 'debug'].includes(process.env.NODE_ENV || 'development'),
    isProd: process.env.NODE_ENV === 'production',

    // Server
    port: parseInt(process.env.PORT || '5000', 10),
    queuePrefix,

    // MongoDB
    mongoDbUri: process.env.MONGODB_URI || '',
    mongoDbName: process.env.MONGODB_DB_NAME || 'yt-downloader',

    // Redis
    redisConfig: {
        uri: process.env.REDIS_URI || 'redis://localhost:6379/0',
    },

    // JWT
    jwt: {
        publicSecret: process.env.JWT_PUBLIC_SECRET || 'yt-downloader-public-secret',
        privateSecret: process.env.JWT_PRIVATE_SECRET || 'yt-downloader-private-secret',
        privateExpiration: parseInt(process.env.JWT_PRIVATE_EXPIRATION || '604800', 10),
    },

    // Google OAuth
    google: {
        clientId: process.env.GOOGLE_CLIENT_ID || '',
        clientSecret: process.env.GOOGLE_CLIENT_SECRET || '',
        redirectUri: process.env.GOOGLE_REDIRECT_URI || '',
    },

    // YouTube
    youtubeApiKey: process.env.YOUTUBE_API_KEY || '',

    // S3 / SeaweedFS
    s3: {
        endpointUrl: process.env.S3_ENDPOINT_URL || '',
        accessKey: process.env.S3_ACCESS_KEY || '',
        secretKey: process.env.S3_SECRET_KEY || '',
        region: process.env.S3_REGION || 'us-east-1',
        bucketName: process.env.S3_BUCKET_NAME || 'yt-downloader',
        keyPrefix: process.env.S3_KEY_PREFIX || 'videos/',
    },

    // Queue names
    queues: {
        download: process.env.QUEUE_DOWNLOAD || `${queuePrefix}queue:download`,
        encode: process.env.QUEUE_ENCODE || `${queuePrefix}queue:encode`,
    },

    // Public API
    publicApi: {
        rateLimit: parseInt(process.env.PUBLIC_API_RATE_LIMIT || '10', 10),
        maxClipDuration: parseInt(process.env.PUBLIC_API_MAX_CLIP_DURATION || '40', 10),
        maxEncodeDuration: parseInt(process.env.PUBLIC_API_MAX_ENCODE_DURATION || '300', 10),
    },

    // Application limits
    maxVideoDuration: parseInt(process.env.MAX_VIDEO_DURATION || '3600', 10),
    maxUploadSizeMb: parseInt(process.env.MAX_UPLOAD_SIZE_MB || '500', 10),
    allowedVideoFormats: (process.env.ALLOWED_VIDEO_FORMATS || 'mp4,avi,mkv,mov,flv,wmv,webm,m4v,mpg,mpeg,3gp').split(','),
    videoRetentionMinutes: parseInt(process.env.VIDEO_RETENTION_MINUTES || '30', 10),
    defaultVideoFormat: process.env.DEFAULT_VIDEO_FORMAT || 'mp4',
    defaultVideoResolution: process.env.DEFAULT_VIDEO_RESOLUTION || 'best',

    // Logging
    logLevel: process.env.LOG_LEVEL || 'INFO',
};

function validateConfig(): void {
    const required = ['mongoDbUri'] as const;
    const missing = required.filter((key) => !config[key]);
    if (missing.length > 0) {
        throw new Error(`Missing required config: ${missing.join(', ')}`);
    }
}

export { config, validateConfig };
