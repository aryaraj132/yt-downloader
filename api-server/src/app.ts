/**
 * Express app setup — middleware, routes, error handlers.
 * Follows the same pattern as app-backend/api/app.js.
 */
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import cookieParser from 'cookie-parser';
import morgan from 'morgan';
import createError from 'http-errors';
import bodyParserErrorHandler from 'express-body-parser-error-handler';
import { sleep } from '@aryaraj132/corekit-js/utils';
import { winstonLogger } from './infra/loggers/winstonLogger';

// Route imports
import authRoutes from './routes/auth';
import videoRoutes from './routes/video';
import encodeRoutes from './routes/encode';
import jobsRoutes from './routes/jobs';
import publicApiRoutes from './routes/publicApi';

// Uncaught exception handler (same pattern as reference)
process.on('uncaughtException', async (err) => {
    try {
        winstonLogger.error('Unhandled Exception Found', { message: err.message }, err);
    } finally {
        await sleep(5000);
        winstonLogger.error('Exiting application due to Unhandled Exception', err.message, err);
        process.exit(1);
    }
});

const app = express();

// CORS
const corsOptions = { origin: true, credentials: true };
app.use(cors(corsOptions));
app.options('*', cors(corsOptions));

app.all('/*', (_req, res, next) => {
    res.header(
        'Access-Control-Allow-Headers',
        'Content-Type,accept,Authorization,X-Browser-Fingerprint'
    );
    res.header('Access-Control-Allow-Methods', 'POST, PUT, GET, DELETE, OPTIONS');
    next();
});

// Logging (skip non-error in prod, same pattern as reference)
app.use(
    morgan('dev', {
        skip(_req, res) {
            return res.statusCode < 500;
        },
    })
);

// Body parsing
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: false }));
app.use(bodyParserErrorHandler());
app.use(cookieParser());
app.use(compression());
app.use(helmet({ frameguard: false }));

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/video', videoRoutes);
app.use('/api/encode', encodeRoutes);
app.use('/api/jobs', jobsRoutes);
app.use('/api/public', publicApiRoutes);

// Health & root
app.get('/health', (_req, res) => {
    res.json({ status: 'healthy', service: 'yt-downloader-api' });
});

app.get('/', (_req, res) => {
    res.json({
        service: 'YouTube Video Downloader API',
        version: '2.0.0',
        architecture: 'api-server + worker',
        endpoints: {
            auth: '/api/auth',
            video: '/api/video',
            encode: '/api/encode',
            jobs: '/api/jobs',
            public: '/api/public',
            health: '/health',
        },
    });
});

// 404 handler (same pattern as reference)
app.use((req, res, next) => {
    if (!res.headersSent) {
        next(createError(404));
    }
});

// Error handler (same pattern as reference)
app.use((err: any, req: express.Request, res: express.Response, _next: express.NextFunction) => {
    res.locals.message = err.message;
    res.locals.error = req.app.get('env') === 'development' ? err : {};

    if (err.name === 'ValidationError') {
        const errorMessage =
            typeof err.message === 'string' ? { message: err.message } : err.message;
        res.status(400).json({
            error: 'ValidationError',
            success: false,
            status: 'error',
            ...errorMessage,
        });
        return;
    }

    if (!res.headersSent) {
        res.status(err.status || 500).json({
            error: 'error',
            message: `Some Internal Error Occurred: ${err.status || 500}`,
        });
    }

    if (res.statusCode !== 404) {
        winstonLogger.error(
            'Error Thrown',
            `Caught at Central error Middleware: ${res.statusCode}`,
            err,
            req
        );
    }
});

export default app;
