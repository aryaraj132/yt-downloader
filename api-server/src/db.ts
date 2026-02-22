import mongoose from 'mongoose';
import { config } from './config';
import { winstonLogger } from './infra/loggers/winstonLogger';

let isConnected = false;

export async function connectDB(): Promise<void> {
    if (isConnected) return;

    try {
        await mongoose.connect(config.mongoDbUri, {
            dbName: config.mongoDbName,
        });
        isConnected = true;
        winstonLogger.info(`MongoDB connected to ${config.mongoDbName}`);
    } catch (error) {
        winstonLogger.error('MongoDB connection error', '', error);
        throw error;
    }
}

export function getDB() {
    return mongoose.connection.db;
}
