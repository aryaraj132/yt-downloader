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

export interface EncodingStatus {
    encode_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    original_filename: string;
    video_codec: string;
    quality_preset: string;
    created_at: string;
    encoding_started_at?: string;
    file_available: boolean;
    file_size_mb?: number;
    error_message?: string;
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

    async startEncoding(encodeId: string, data: StartEncodingData): Promise<{ message: string; encode_id: string; file_size_mb?: number }> {
        const response = await api.post(`/encode/start/${encodeId}`, data);
        return response.data;
    },

    async getEncodingStatus(encodeId: string): Promise<EncodingStatus> {
        const response = await api.get(`/encode/status/${encodeId}`);
        return response.data;
    },

    async downloadEncodedVideo(encodeId: string): Promise<Blob> {
        const response = await api.post(`/encode/download/${encodeId}`, {}, {
            responseType: 'blob',
        });
        return response.data;
    },

    async getSupportedCodecs(): Promise<SupportedCodecs> {
        const response = await api.get('/encode/codecs');
        return response.data;
    },
};
