import { Request, Response, NextFunction } from 'express';
import { verifyPrivateToken, verifyPublicToken } from '../utils/token';
import { Session } from '../models/Session';
import { getRedis } from '../redis';
import { winstonLogger } from '../infra/loggers/winstonLogger';
import crypto from 'crypto';

// Extend Express Request to include user info
declare global {
    namespace Express {
        interface Request {
            userId?: string;
            sessionId?: string;
            tokenType?: 'public' | 'private';
        }
    }
}

function extractToken(req: Request): string | null {
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
        return authHeader.substring(7);
    }
    return null;
}

/**
 * Middleware to require a valid private token.
 * Sets req.userId and req.sessionId on success.
 */
export async function requirePrivateToken(
    req: Request,
    res: Response,
    next: NextFunction
): Promise<void> {
    try {
        const token = extractToken(req);
        if (!token) {
            res.status(401).json({ error: 'Authentication token required' });
            return;
        }

        const payload = verifyPrivateToken(token);
        if (!payload || payload.type !== 'private') {
            res.status(401).json({ error: 'Invalid or expired token' });
            return;
        }

        // Check session in Redis first, then MongoDB
        const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
        const redis = getRedis();
        let sessionValid = false;

        try {
            const cached = await redis.get(`session:${tokenHash}`);
            if (cached) {
                sessionValid = true;
            }
        } catch {
            // Redis unavailable, fall through to MongoDB
        }

        if (!sessionValid) {
            const session = await Session.findOne({
                _id: payload.session_id,
                user_id: payload.user_id,
                expires_at: { $gt: new Date() },
            });

            if (!session) {
                res.status(401).json({ error: 'Session expired or invalid' });
                return;
            }

            // Cache in Redis for future lookups
            try {
                await redis.set(
                    `session:${tokenHash}`,
                    JSON.stringify({ user_id: payload.user_id }),
                    'EX',
                    86400 // 1 day
                );
            } catch {
                // Redis write failure is non-fatal
            }
        }

        req.userId = payload.user_id;
        req.sessionId = payload.session_id;
        req.tokenType = 'private';
        next();
    } catch (error) {
        winstonLogger.error('Private token verification error', '', error);
        res.status(401).json({ error: 'Authentication failed' });
    }
}

/**
 * Middleware to require a valid public token.
 * Sets req.userId on success.
 */
export async function requirePublicToken(
    req: Request,
    res: Response,
    next: NextFunction
): Promise<void> {
    try {
        const token = extractToken(req);
        if (!token) {
            res.status(401).json({ error: 'Public API token required' });
            return;
        }

        const payload = verifyPublicToken(token);
        if (!payload || payload.type !== 'public') {
            res.status(401).json({ error: 'Invalid public token' });
            return;
        }

        req.userId = payload.user_id;
        req.tokenType = 'public';
        next();
    } catch (error) {
        winstonLogger.error('Public token verification error', '', error);
        res.status(401).json({ error: 'Authentication failed' });
    }
}
