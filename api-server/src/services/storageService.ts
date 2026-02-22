import {
    S3Client,
    PutObjectCommand,
    DeleteObjectCommand,
    GetObjectCommand,
    HeadBucketCommand,
    CreateBucketCommand,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { config } from '../config';
import { winstonLogger } from '../infra/loggers/winstonLogger';
import fs from 'fs';
import path from 'path';

let s3Client: S3Client | null = null;

function getClient(): S3Client {
    if (!s3Client) {
        s3Client = new S3Client({
            endpoint: config.s3.endpointUrl || undefined,
            region: config.s3.region,
            credentials: {
                accessKeyId: config.s3.accessKey,
                secretAccessKey: config.s3.secretKey,
            },
            forcePathStyle: true, // Required for SeaweedFS / MinIO
        });
    }
    return s3Client;
}

export const storageService = {
    async ensureBucket(): Promise<void> {
        const client = getClient();
        try {
            await client.send(new HeadBucketCommand({ Bucket: config.s3.bucketName }));
        } catch {
            try {
                await client.send(new CreateBucketCommand({ Bucket: config.s3.bucketName }));
                winstonLogger.info(`S3 bucket created: ${config.s3.bucketName}`);
            } catch (err) {
                winstonLogger.error('Failed to create S3 bucket', '', err);
            }
        }
    },

    async uploadFile(
        filePath: string,
        objectName?: string,
        contentType?: string
    ): Promise<[boolean, string]> {
        try {
            const client = getClient();
            const key = objectName || path.basename(filePath);
            const fileStream = fs.createReadStream(filePath);

            await client.send(
                new PutObjectCommand({
                    Bucket: config.s3.bucketName,
                    Key: key,
                    Body: fileStream,
                    ContentType: contentType || 'application/octet-stream',
                })
            );

            winstonLogger.info(`S3 uploaded ${filePath} as ${key}`);
            return [true, key];
        } catch (error: any) {
            winstonLogger.error('S3 upload failed', error.message, error);
            return [false, error.message];
        }
    },

    async uploadBuffer(
        buffer: Buffer,
        objectName: string,
        contentType?: string
    ): Promise<[boolean, string]> {
        try {
            const client = getClient();

            await client.send(
                new PutObjectCommand({
                    Bucket: config.s3.bucketName,
                    Key: objectName,
                    Body: buffer,
                    ContentType: contentType || 'application/octet-stream',
                })
            );

            winstonLogger.info(`S3 uploaded buffer as ${objectName}`);
            return [true, objectName];
        } catch (error: any) {
            winstonLogger.error('S3 buffer upload failed', error.message, error);
            return [false, error.message];
        }
    },

    async deleteFile(objectName: string): Promise<boolean> {
        try {
            const client = getClient();
            await client.send(
                new DeleteObjectCommand({
                    Bucket: config.s3.bucketName,
                    Key: objectName,
                })
            );
            winstonLogger.info(`S3 deleted ${objectName}`);
            return true;
        } catch (error: any) {
            winstonLogger.error('S3 delete failed', error.message, error);
            return false;
        }
    },

    async getPresignedUrl(objectName: string, expiresIn: number = 3600): Promise<string | null> {
        try {
            const client = getClient();
            const url = await getSignedUrl(
                client,
                new GetObjectCommand({
                    Bucket: config.s3.bucketName,
                    Key: objectName,
                }),
                { expiresIn }
            );
            return url;
        } catch (error: any) {
            winstonLogger.error('S3 presigned URL failed', error.message, error);
            return null;
        }
    },

    /**
     * Build a direct S3 URL (useful when bucket is publicly accessible or using SeaweedFS).
     */
    getDirectUrl(objectName: string): string {
        return `${config.s3.endpointUrl}/${config.s3.bucketName}/${objectName}`;
    },
};
