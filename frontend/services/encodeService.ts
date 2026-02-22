import api from '@/lib/api';

export interface UploadResponse {
    message: string;
    encode_id: string;
    original_filename: string;
    file_size_mb: number;
    metadata?: {
        duration: number;
        resolution: string;
        original_codec: string;
    };
}

export interface StartEncodingData {
    video_codec: 'h264' | 'h265' | 'av1';
    quality_preset: 'lossless' | 'high' | 'medium';
}

export interface EncodingProgress {
    current_phase: 'downloading_source' | 'encoding' | 'uploading' | 'completed' | 'failed' | 'initializing';
    download_progress: number;
    encoding_progress: number;
    status?: string;
}

export interface EncodingStatus {
    encode_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: EncodingProgress;
    original_filename: string;
    video_codec: string;
    quality_preset: string;
    created_at: string;
    encoding_started_at?: string;
    encoding_completed_at?: string;
    encoding_duration_seconds?: number;
    file_available: boolean;
    file_size_mb?: number;
    error_message?: string;
    download_url?: string;
    job_id?: string;
}

export interface SupportedCodecs {
    codecs: Record<string, string[]>;
}

export const encodeService = {
    async uploadVideo(file: File): Promise<UploadResponse> {
        const formData = new FormData();
        formData.append('video', file);

        const response = await api.post('/encode/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    async startEncoding(encodeId: string, data: StartEncodingData): Promise<{ message: string; encode_id: string; job_id: string; status: string; file_size_mb?: number }> {
        const response = await api.post(`/encode/start/${encodeId}`, data);
        return response.data;
    },

    async getEncodingStatus(encodeId: string): Promise<EncodingStatus> {
        const response = await api.get(`/encode/status/${encodeId}`);
        return response.data;
    },

    async downloadEncodedVideo(encodeId: string): Promise<{ download_url: string; message: string }> {
        const response = await api.post(`/encode/download/${encodeId}`);
        return response.data;
    },

    async getSupportedCodecs(): Promise<SupportedCodecs> {
        const response = await api.get('/encode/codecs');
        return response.data;
    },

    // ========== PUBLIC API METHODS (no authentication) ==========

    async encodePublic(file: File, options: {
        video_codec: 'h264' | 'h265' | 'av1';
        quality_preset: 'lossless' | 'high' | 'medium';
    }): Promise<{
        job_id: string;
        message: string;
        status_url: string;
        download_url: string;
        rate_limit: { remaining: number; limit: number; reset_at: string };
    }> {
        // Get video duration client-side
        const duration = await this.getVideoDuration(file);

        const formData = new FormData();
        formData.append('video', file);
        formData.append('video_codec', options.video_codec);
        formData.append('quality_preset', options.quality_preset);
        formData.append('duration', duration.toString());

        const { publicApi } = await import('@/lib/api');
        const response = await publicApi.post('/public/encode', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    // Helper: Get video duration from File using HTML5
    getVideoDuration(file: File): Promise<number> {
        return new Promise((resolve, reject) => {
            const video = document.createElement('video');
            video.preload = 'metadata';

            video.onloadedmetadata = () => {
                window.URL.revokeObjectURL(video.src);
                resolve(video.duration);
            };

            video.onerror = () => {
                reject(new Error('Failed to load video metadata'));
            };

            video.src = URL.createObjectURL(file);
        });
    }
};
