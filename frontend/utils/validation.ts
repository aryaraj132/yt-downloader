import { z } from 'zod';

export const youtubeUrlSchema = z.string().refine(
    (url) => {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[a-zA-Z0-9_-]{11}/;
        return youtubeRegex.test(url);
    },
    {
        message: 'Please enter a valid YouTube URL',
    }
);

export const emailSchema = z.string().email('Please enter a valid email address');

export const passwordSchema = z
    .string()
    .min(8, 'Password must be at least 8 characters long');

export const timeRangeSchema = z.object({
    start_time: z.number().min(0, 'Start time must be positive'),
    end_time: z.number().min(0, 'End time must be positive'),
}).refine(
    (data) => data.end_time > data.start_time,
    {
        message: 'End time must be greater than start time',
        path: ['end_time'],
    }
).refine(
    (data) => (data.end_time - data.start_time) <= 120,
    {
        message: 'Video segment cannot exceed 120 seconds',
        path: ['end_time'],
    }
);

export const extractYoutubeVideoId = (url: string): string | null => {
    const patterns = [
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/,
        /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})/,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
    ];

    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) {
            return match[1];
        }
    }

    return null;
};
