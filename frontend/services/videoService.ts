import api from '@/lib/api';

export interface SaveVideoData {
    url: string;
    start_time: number;
    end_time: number;
    user_id: string;
    additional_message?: string;
    clip_offset?: number;
}

export interface DownloadPreferences {
    format_preference?: 'mp4' | 'webm' | 'best';
    resolution_preference?: '720p' | '1080p' | '1440p' | '2160p' | '4320p' | 'best';
    cookies?: string;
}

export interface VideoProgress {
    current_phase: 'downloading' | 'encoding' | 'initializing';
    download_progress: number;
    encoding_progress: number;
    speed?: string;
    eta?: string;
    fps?: number;
}

export interface VideoStatus {
    video_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    url: string;
    start_time: number;
    end_time: number;
    created_at: string;
    file_available: boolean;
    available_formats?: string[];
    progress?: VideoProgress;
    error_message?: string;
}

export interface Video {
    video_id: string;
    url: string;
    start_time: number;
    end_time: number;
    status: string;
    created_at: string;
    file_available: boolean;
    youtube_video_id?: string;
    clipped_by?: string;
}

export interface PaginationInfo {
    page: number;
    limit: number;
    total: number;
    has_more: boolean;
}

export const videoService = {
    async saveVideoInfo(data: SaveVideoData, publicToken: string): Promise<{ message: string; video_id: string }> {
        const response = await api.post('/video/save', data, {
            headers: {
                Authorization: `Bearer ${publicToken}`,
            },
        });
        return response.data;
    },

    async getAvailableResolutions(url: string, cookies?: string): Promise<{ video_id: string; url: string; resolutions: string[] }> {
        const response = await api.post('/video/resolutions', { url, cookies });
        return response.data;
    },

    async downloadVideo(videoId: string, preferences?: DownloadPreferences): Promise<Blob | { download_url: string }> {
        const response = await api.post(`/video/download/${videoId}`, preferences || {}, {
            responseType: 'blob',
        });

        // Check if response is JSON (redirect URL)
        if (response.headers['content-type']?.includes('application/json')) {
            const text = await response.data.text();
            const json = JSON.parse(text);
            if (json.download_url) {
                return { download_url: json.download_url };
            }
        }

        return response.data;
    },

    async getVideoStatus(videoId: string): Promise<VideoStatus> {
        const response = await api.get(`/video/status/${videoId}`);
        return response.data;
    },

    async listUserVideos(page: number = 1, limit: number = 20): Promise<{ videos: Video[]; pagination: PaginationInfo }> {
        const response = await api.get(`/video/list?page=${page}&limit=${limit}`);
        return response.data;
    },

    async getAvailableFormats(videoId: string, cookies?: string): Promise<{
        video_id: string;
        resolutions: string[];
        extensions: string[];
        formats: Record<string, string[]>;
    }> {
        // Changed to POST to support sending cookies in body
        const response = await api.post(`/video/formats`, { video_id: videoId, cookies });
        return response.data;
    },

    // ========== PUBLIC API METHODS (no authentication) ==========

    async savePublicClip(data: {
        url: string;
        start_time: number;
        end_time: number;
        cookies?: string;
        format?: string;
        resolution?: string;
    }): Promise<{
        job_id: string;
        message: string;
        status_url: string;
        download_url: string;
        rate_limit: { remaining: number; limit: number; reset_at: string };
    }> {
        const { publicApi } = await import('@/lib/api');
        const response = await publicApi.post('/public/clip', data);
        return response.data;
    },

    async getPublicJobStatus(jobId: string): Promise<{
        job_id: string;
        status: string;
        progress: number;
        current_phase: string;
        file_ready: boolean;
        error_message?: string;
    }> {
        const { publicApi } = await import('@/lib/api');
        const response = await publicApi.get(`/public/status/${jobId}`);
        return response.data;
    },

    async downloadPublicFile(jobId: string): Promise<string> {
        const { publicApi } = await import('@/lib/api');
        const response = await publicApi.get(`/public/download/${jobId}`, {
            responseType: 'blob'
        });

        // Check if response is JSON (redirect URL)
        if (response.headers['content-type']?.includes('application/json')) {
            const text = await response.data.text();
            const json = JSON.parse(text);
            if (json.download_url) {
                return json.download_url;
            }
        }

        const blob = new Blob([response.data]);
        const url = window.URL.createObjectURL(blob);
        return url;
    },

    async checkRateLimit(): Promise<{
        limit: number;
        used: number;
        remaining: number;
        reset_at: string;
    }> {
        const { publicApi } = await import('@/lib/api');
        const response = await publicApi.get('/public/rate-limit');
        return response.data;
    }
};
