'use client';

import React from 'react';
import { Video } from '@/services/videoService';
import { Button } from './ui/Button';
import { Download, Trash2, Share2, Clock, Calendar } from 'lucide-react';
import { extractYoutubeVideoId } from '@/utils/validation';

interface VideoCardProps {
    video: Video;
    onDownload: (videoId: string) => void;
    onDelete: (videoId: string) => void;
    onShare?: (videoId: string) => void;
}

export const VideoCard: React.FC<VideoCardProps> = ({
    video,
    onDownload,
    onDelete,
    onShare,
}) => {
    const youtubeId = extractYoutubeVideoId(video.url);
    const thumbnailUrl = youtubeId
        ? `https://i.ytimg.com/vi/${youtubeId}/mqdefault.jpg`
        : '/placeholder-video.png';

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'bg-green-500';
            case 'processing':
                return 'bg-yellow-500';
            case 'failed':
                return 'bg-red-500';
            default:
                return 'bg-gray-500';
        }
    };

    return (
        <div className="glass-effect rounded-xl overflow-hidden hover:shadow-xl transition-all duration-300">
            {/* Thumbnail */}
            <div className="relative aspect-video bg-gray-200 dark:bg-gray-700">
                <img
                    src={thumbnailUrl}
                    alt="Video thumbnail"
                    className="w-full h-full object-cover"
                />
                <div className={`absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium text-white ${getStatusColor(video.status)}`}>
                    {video.status}
                </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-3">
                {/* URL - truncated */}
                <div className="text-sm text-gray-600 dark:text-gray-400 truncate">
                    {video.url}
                </div>

                {/* Time info */}
                <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center space-x-1">
                        <Clock size={14} />
                        <span>{video.start_time}s - {video.end_time}s</span>
                    </div>
                    <div className="flex items-center space-x-1">
                        <Calendar size={14} />
                        <span>{formatDate(video.created_at)}</span>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2 pt-2">
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={() => onDownload(video.video_id)}
                        disabled={!video.file_available && video.status !== 'pending'}
                        className="flex-1"
                    >
                        <Download size={16} className="mr-1" />
                        Download
                    </Button>
                    {onShare && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onShare(video.video_id)}
                        >
                            <Share2 size={16} />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(video.video_id)}
                    >
                        <Trash2 size={16} />
                    </Button>
                </div>
            </div>
        </div>
    );
};
