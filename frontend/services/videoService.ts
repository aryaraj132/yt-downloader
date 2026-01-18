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

    async downloadVideo(videoId: string, preferences?: DownloadPreferences): Promise<Blob> {
        const response = await api.post(`/video/download/${videoId}`, preferences || {}, {
            responseType: 'blob',
        });
        return response.data;
    },

    async getVideoStatus(videoId: string): Promise<VideoStatus> {
        const response = await api.get(`/video/status/${videoId}`);
        return response.data;
    },

    async listUserVideos(): Promise<{ videos: Video[] }> {
        const response = await api.get('/video/list');
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
};
