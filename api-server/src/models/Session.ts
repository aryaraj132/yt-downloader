import mongoose, { Schema, Document, Types } from 'mongoose';

export interface ISession extends Document {
    user_id: Types.ObjectId;
    token: string;
    created_at: Date;
    expires_at: Date;
}

const SessionSchema = new Schema<ISession>(
    {
        user_id: { type: Schema.Types.ObjectId, ref: 'User', required: true, index: true },
        token: { type: String, required: true, unique: true },
        created_at: { type: Date, default: Date.now },
        expires_at: { type: Date, required: true, index: true },
    },
    {
        collection: 'sessions',
    }
);

SessionSchema.index({ token: 1 }, { unique: true });
SessionSchema.index({ expires_at: 1 }, { expireAfterSeconds: 0 });

export const Session = mongoose.model<ISession>('Session', SessionSchema);
