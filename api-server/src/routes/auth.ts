import { Router, Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import crypto from 'crypto';
import { User } from '../models/User';
import { Session } from '../models/Session';
import { requirePrivateToken } from '../middleware/auth';
import { generatePrivateToken, generatePublicToken } from '../utils/token';
import { validateEmail, validatePassword } from '../utils/validators';
import { config } from '../config';
import { getRedis } from '../redis';
import { winstonLogger } from '../infra/loggers/winstonLogger';

const router = Router();

// POST /api/auth/register
router.post('/register', async (req: Request, res: Response) => {
    try {
        const { email, password } = req.body;

        const [validEmail, emailErr] = validateEmail(email);
        if (!validEmail) return res.status(400).json({ error: emailErr });

        const [validPass, passErr] = validatePassword(password);
        if (!validPass) return res.status(400).json({ error: passErr });

        const existing = await User.findOne({ email: email.toLowerCase() });
        if (existing) return res.status(409).json({ error: 'Email already registered' });

        const passwordHash = await bcrypt.hash(password, 12);
        const user = await User.create({
            email: email.toLowerCase(),
            password_hash: passwordHash,
        });

        res.status(201).json({
            message: 'User registered successfully',
            user_id: user._id.toString(),
        });
    } catch (error: any) {
        winstonLogger.error('Register error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/auth/login
router.post('/login', async (req: Request, res: Response) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({ error: 'Email and password are required' });
        }

        const user = await User.findOne({ email: email.toLowerCase() });
        if (!user) return res.status(401).json({ error: 'Invalid credentials' });

        const valid = await bcrypt.compare(password, user.password_hash);
        if (!valid) return res.status(401).json({ error: 'Invalid credentials' });

        // Create session
        const expiresAt = new Date(Date.now() + config.jwt.privateExpiration * 1000);
        const session = await Session.create({
            user_id: user._id,
            token: '', // Will be updated after token generation
            created_at: new Date(),
            expires_at: expiresAt,
        });

        const token = generatePrivateToken(user._id.toString(), session._id.toString());

        // Update session with token
        session.token = token;
        await session.save();

        // Cache session in Redis
        try {
            const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
            const redis = getRedis();
            await redis.set(
                `session:${tokenHash}`,
                JSON.stringify({ user_id: user._id.toString(), email: user.email }),
                'EX',
                config.jwt.privateExpiration
            );
        } catch {
            // Redis cache failure is non-fatal
        }

        res.json({
            message: 'Login successful',
            token,
            user: {
                id: user._id.toString(),
                email: user.email,
            },
        });
    } catch (error: any) {
        winstonLogger.error('Login error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/auth/logout
router.post('/logout', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        // Delete session from DB
        if (req.sessionId) {
            await Session.deleteOne({ _id: req.sessionId });
        }

        // Remove from Redis cache
        try {
            const token = req.headers.authorization?.substring(7);
            if (token) {
                const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
                const redis = getRedis();
                await redis.del(`session:${tokenHash}`);
            }
        } catch {
            // Non-fatal
        }

        res.json({ message: 'Logout successful' });
    } catch (error: any) {
        winstonLogger.error('Logout error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/auth/change-password
router.post('/change-password', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const { current_password, new_password } = req.body;

        if (!current_password || !new_password) {
            return res.status(400).json({ error: 'Current and new passwords are required' });
        }

        const [validPass, passErr] = validatePassword(new_password);
        if (!validPass) return res.status(400).json({ error: passErr });

        const user = await User.findById(req.userId);
        if (!user) return res.status(404).json({ error: 'User not found' });

        const valid = await bcrypt.compare(current_password, user.password_hash);
        if (!valid) return res.status(401).json({ error: 'Current password is incorrect' });

        user.password_hash = await bcrypt.hash(new_password, 12);
        await user.save();

        // Invalidate all sessions
        await Session.deleteMany({ user_id: user._id });

        res.json({ message: 'Password changed successfully. Please login again.' });
    } catch (error: any) {
        winstonLogger.error('Change password error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/auth/me
router.get('/me', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const user = await User.findById(req.userId).select('email created_at');
        if (!user) return res.status(404).json({ error: 'User not found' });

        res.json({
            user: {
                id: user._id.toString(),
                email: user.email,
            },
        });
    } catch (error: any) {
        console.error('[Auth] Get user error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// GET /api/auth/token/public
router.get('/token/public', requirePrivateToken, async (req: Request, res: Response) => {
    try {
        const user = await User.findById(req.userId);
        if (!user) return res.status(404).json({ error: 'User not found' });

        // Generate or return existing public token
        if (!user.public_token) {
            user.public_token = generatePublicToken(user._id.toString());
            await user.save();
        }

        res.json({
            token: user.public_token,
            expires_in: null, // Public tokens don't expire
        });
    } catch (error: any) {
        winstonLogger.error('Get public token error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /api/auth/google/login — Google OAuth callback
router.post('/google/login', async (req: Request, res: Response) => {
    try {
        const { credential, google_id, email: googleEmail } = req.body;

        if (!googleEmail || !google_id) {
            return res.status(400).json({ error: 'Google credentials required' });
        }

        // Find or create user
        let user = await User.findOne({ $or: [{ google_id }, { email: googleEmail.toLowerCase() }] });

        if (!user) {
            // Create new user with Google
            const randomPass = crypto.randomBytes(32).toString('hex');
            user = await User.create({
                email: googleEmail.toLowerCase(),
                password_hash: await bcrypt.hash(randomPass, 12),
                google_id,
            });
        } else if (!user.google_id) {
            // Link existing email account with Google
            user.google_id = google_id;
            await user.save();
        }

        // Create session
        const expiresAt = new Date(Date.now() + config.jwt.privateExpiration * 1000);
        const session = await Session.create({
            user_id: user._id,
            token: '',
            created_at: new Date(),
            expires_at: expiresAt,
        });

        const token = generatePrivateToken(user._id.toString(), session._id.toString());
        session.token = token;
        await session.save();

        // Cache in Redis
        try {
            const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
            const redis = getRedis();
            await redis.set(
                `session:${tokenHash}`,
                JSON.stringify({ user_id: user._id.toString(), email: user.email }),
                'EX',
                config.jwt.privateExpiration
            );
        } catch {
            // Non-fatal
        }

        res.json({
            message: 'Login successful',
            token,
            user: {
                id: user._id.toString(),
                email: user.email,
            },
        });
    } catch (error: any) {
        winstonLogger.error('Google login error', error.message, error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

export default router;
