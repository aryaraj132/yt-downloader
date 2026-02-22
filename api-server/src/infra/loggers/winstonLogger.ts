/**
 * Winston Logger Service using corekit-js WinstonLoggerService.
 * Provides structured logging across the application.
 */
import { WinstonLoggerService } from '@aryaraj132/corekit-js/logger';
import { config } from '../../config';

export const winstonLogger = new WinstonLoggerService({
    serviceName: config.serviceName,
    environment: config.environment,
    containerAppName: config.containerAppName,
    containerAppReplicaName: config.containerId,
});

export { WinstonLoggerService };
