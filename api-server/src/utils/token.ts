import jwt from 'jsonwebtoken';
import { config } from '../config';

interface TokenPayload {
    user_id: string;
    session_id?: string;
    type: 'public' | 'private';
    exp?: number;
}

export function generatePrivateToken(userId: string, sessionId: string): string {
    const payload: TokenPayload = {
        user_id: userId,
        session_id: sessionId,
        type: 'private',
    };
    return jwt.sign(payload, config.jwt.privateSecret, {
        expiresIn: config.jwt.privateExpiration,
    });
}

export function generatePublicToken(userId: string): string {
    const payload: TokenPayload = {
        user_id: userId,
        type: 'public',
    };
    // Public tokens don't expire
    return jwt.sign(payload, config.jwt.publicSecret);
}

export function verifyPrivateToken(token: string): TokenPayload | null {
    try {
        return jwt.verify(token, config.jwt.privateSecret) as TokenPayload;
    } catch {
        return null;
    }
}

export function verifyPublicToken(token: string): TokenPayload | null {
    try {
        return jwt.verify(token, config.jwt.publicSecret) as TokenPayload;
    } catch {
        return null;
    }
}
