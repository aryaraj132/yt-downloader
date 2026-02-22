/**
 * HTTP server entry point.
 * Follows the same pattern as app-backend/api/bin/www.
 */
import dotenv from 'dotenv';
import path from 'path';
import http from 'http';

// Load env first (before any imports that use config)
if (process.env.NODE_ENV !== 'production') {
    dotenv.config({ path: path.resolve(__dirname, '../../../.env') });
}

import { config, validateConfig } from '../config';
import { connectDB } from '../db';
import { getRedis } from '../redis';
import { storageService } from '../services/storageService';
import { winstonLogger } from '../infra/loggers/winstonLogger';
import app from '../app';

function onError(error: NodeJS.ErrnoException) {
    if (error.syscall !== 'listen') {
        throw error;
    }
    switch (error.code) {
        case 'EACCES':
            winstonLogger.error(`${config.port} requires elevated privileges`);
            process.exit(1);
            break;
        case 'EADDRINUSE':
            winstonLogger.error(`${config.port} is already in use`);
            process.exit(1);
            break;
        default:
            throw error;
    }
}

async function start() {
    try {
        // Validate config
        validateConfig();

        // Connect to MongoDB
        await connectDB();
        winstonLogger.info('MongoDB connected');

        // Verify Redis
        const redis = getRedis();
        await redis.ping();
        winstonLogger.info('Redis connection verified');

        // Ensure S3 bucket exists
        if (config.s3.endpointUrl) {
            await storageService.ensureBucket();
            winstonLogger.info('S3 bucket verified');
        }

        // Create HTTP server
        app.set('port', config.port);
        const server = http.createServer(app);

        server.setTimeout(6 * 60 * 1000); // 6 minutes
        server.on('error', onError);
        server.on('listening', () => winstonLogger.info(`Listening on ${config.port}`));
        server.listen(config.port);

    } catch (error: any) {
        winstonLogger.error('Failed to start server', error.message, error);
        process.exit(1);
    }
}

start();
