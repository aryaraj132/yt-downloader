import mongoose, { Schema, Document } from 'mongoose';

export interface IUser extends Document {
    email: string;
    password_hash: string;
    google_id?: string;
    created_at: Date;
    updated_at: Date;
    public_token?: string;
}

const UserSchema = new Schema<IUser>(
    {
        email: { type: String, required: true, unique: true, lowercase: true, trim: true },
        password_hash: { type: String, required: true },
        google_id: { type: String, sparse: true },
        public_token: { type: String, sparse: true },
    },
    {
        timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' },
        collection: 'users',
    }
);

UserSchema.index({ email: 1 }, { unique: true });
UserSchema.index({ google_id: 1 }, { sparse: true });
UserSchema.index({ public_token: 1 }, { sparse: true });

export const User = mongoose.model<IUser>('User', UserSchema);
