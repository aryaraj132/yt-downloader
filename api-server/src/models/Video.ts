import mongoose, { Schema, Document, Types } from 'mongoose';

export type VideoStatusType = 'pending' | 'processing' | 'completed' | 'failed' | 'expired';
export type SourceType = 'youtube' | 'upload';
export type StorageMode = 'local' | 's3';
export type JobType = 'download' | 'encode';

export interface IVideo extends Document {
    user_id: Types.ObjectId;

    // Source info
    source_type: SourceType;
    url?: string;
    youtube_video_id?: string;

    // Time range (for downloads)
    start_time?: number;
    end_time?: number;

    // Status
    status: VideoStatusType;
    file_path?: string;
    storage_mode?: StorageMode;
    error_message?: string;

    // Format preferences
    format_preference?: string;
    resolution_preference?: string;
    available_formats?: string[];

    // Encoding
    original_filename?: string;
    input_file_path?: string;
    video_codec?: string;
    audio_codec?: string;
    quality_preset?: string;
    encoding_progress?: number;
    encoding_started_at?: Date;
    encoding_completed_at?: Date;

    // Live stream
    additional_message?: string;
    clip_offset?: number;
    chat_id?: string;
    chat_author?: string;
    chat_author_channel_id?: string;
    chat_message?: string;
    is_user_message?: boolean;
    stream_start_time?: Date;
    chat_timestamp?: Date;
    public_token?: string;

    // Metadata
    file_size_bytes?: number;
    job_type?: JobType;
    job_id?: string;
    created_at: Date;
    updated_at: Date;
    expires_at?: Date;
}

const VideoSchema = new Schema<IVideo>(
    {
        user_id: { type: Schema.Types.ObjectId, ref: 'User', required: true, index: true },

        source_type: { type: String, enum: ['youtube', 'upload'], default: 'youtube' },
        url: String,
        youtube_video_id: String,

        start_time: Number,
        end_time: Number,

        status: {
            type: String,
            enum: ['pending', 'processing', 'completed', 'failed', 'expired'],
            default: 'pending',
            index: true,
        },
        file_path: String,
        storage_mode: { type: String, enum: ['local', 's3'], default: 'local' },
        error_message: String,

        format_preference: String,
        resolution_preference: String,
        available_formats: [String],

        original_filename: String,
        input_file_path: String,
        video_codec: String,
        audio_codec: { type: String, default: 'aac' },
        quality_preset: String,
        encoding_progress: { type: Number, default: 0 },
        encoding_started_at: Date,
        encoding_completed_at: Date,

        additional_message: String,
        clip_offset: Number,
        chat_id: String,
        chat_author: String,
        chat_author_channel_id: String,
        chat_message: String,
        is_user_message: Boolean,
        stream_start_time: Date,
        chat_timestamp: Date,
        public_token: String,

        file_size_bytes: Number,
        job_type: { type: String, enum: ['download', 'encode'] },
        job_id: String,
        expires_at: Date,
    },
    {
        timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' },
        collection: 'videos',
    }
);

VideoSchema.index({ user_id: 1, created_at: -1 });
VideoSchema.index({ expires_at: 1 });

export const Video = mongoose.model<IVideo>('Video', VideoSchema);
