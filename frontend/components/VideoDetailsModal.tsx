'use client';

import React, { useState } from 'react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';
import { Select } from './ui/Select';
import { ProgressBar } from './ui/ProgressBar';
import { Video, videoService } from '@/services/videoService';
import { downloadFile } from '@/utils/downloadFile';
import { useToast } from './ui/Toast';
import { Download, Loader, Clock, Calendar } from 'lucide-react';

interface VideoDetailsModalProps {
    video: Video | null;
    isOpen: boolean;
    onClose: () => void;
}

export const VideoDetailsModal: React.FC<VideoDetailsModalProps> = ({
    video,
    isOpen,
    onClose,
}) => {
    const { showToast } = useToast();
    const [selectedFormat, setSelectedFormat] = useState('mp4');
    const [selectedResolution, setSelectedResolution] = useState('1080p');
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState(0);

    if (!video) return null;

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const handleDownload = async () => {
        setIsDownloading(true);
        setDownloadProgress(0);

        try {
            // Poll for status if not ready
            if (!video.file_available) {
                const pollInterval = setInterval(async () => {
                    try {
                        const status = await videoService.getVideoStatus(video.video_id);

                        if (status.progress) {
                            setDownloadProgress(status.progress.download_progress || 0);
                        }

                        if (status.status === 'completed') {
                            clearInterval(pollInterval);

                            // Download the video
                            const blob = await videoService.downloadVideo(video.video_id, {
                                format_preference: selectedFormat as any,
                                resolution_preference: selectedResolution as any,
                            });

                            downloadFile(blob, `video_${video.video_id}.${selectedFormat}`);
                            showToast('Video downloaded successfully!', 'success');
                            setIsDownloading(false);
                            setDownloadProgress(0);
                        } else if (status.status === 'failed') {
                            clearInterval(pollInterval);
                            showToast(status.error_message || 'Download failed', 'error');
                            setIsDownloading(false);
                            setDownloadProgress(0);
                        }
                    } catch (error) {
                        clearInterval(pollInterval);
                        showToast('Error checking download status', 'error');
                        setIsDownloading(false);
                        setDownloadProgress(0);
                    }
                }, 2000);

                // Timeout after 5 minutes
                setTimeout(() => {
                    clearInterval(pollInterval);
                    if (isDownloading) {
                        showToast('Download timeout. Please try again later.', 'warning');
                        setIsDownloading(false);
                    }
                }, 300000);
            } else {
                // File is ready, download directly
                const blob = await videoService.downloadVideo(video.video_id, {
                    format_preference: selectedFormat as any,
                    resolution_preference: selectedResolution as any,
                });

                downloadFile(blob, `video_${video.video_id}.${selectedFormat}`);
                showToast('Video downloaded successfully!', 'success');
                setIsDownloading(false);
            }
        } catch (error: any) {
            if (error.response?.status === 202) {
                showToast('Video is still processing. Please try again later.', 'info');
            } else {
                showToast('Download failed', 'error');
            }
            setIsDownloading(false);
            setDownloadProgress(0);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Video Details">
            <div className="space-y-4">
                {/* YouTube Embed Preview */}
                {video.youtube_video_id && (
                    <div className="aspect-video rounded-xl overflow-hidden bg-gray-900">
                        <iframe
                            width="100%"
                            height="100%"
                            src={`https://www.youtube.com/embed/${video.youtube_video_id}${video.start_time > 0 ? `?start=${video.start_time}` : ''}`}
                            title="YouTube video player"
                            frameBorder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                        />
                    </div>
                )}

                {/* Video Information */}
                <div className="space-y-2 text-sm">
                    <div>
                        <span className="font-semibold text-gray-700 dark:text-gray-300">URL:</span>
                        <p className="text-gray-600 dark:text-gray-400 truncate">{video.url}</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Clock size={16} className="text-gray-500" />
                        <span className="text-gray-600 dark:text-gray-400">
                            Clip: {video.start_time}s - {video.end_time}s ({video.end_time - video.start_time}s duration)
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Calendar size={16} className="text-gray-500" />
                        <span className="text-gray-600 dark:text-gray-400">
                            Clipped on {formatDate(video.created_at)}
                        </span>
                    </div>
                    {video.clipped_by && (
                        <div>
                            <span className="text-gray-600 dark:text-gray-400">
                                Clipped by: <span className="font-medium">{video.clipped_by}</span>
                            </span>
                        </div>
                    )}
                    <div>
                        <span className="font-semibold text-gray-700 dark:text-gray-300">Status:</span>
                        <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${video.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                                video.status === 'processing' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                                    video.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                                        'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                            }`}>
                            {video.status}
                        </span>
                    </div>
                </div>

                {/* Download Controls */}
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-3">Download Options</h4>
                    <div className="grid grid-cols-2 gap-4 mb-4">
                        <Select
                            label="Format"
                            value={selectedFormat}
                            onChange={(e) => setSelectedFormat(e.target.value)}
                            options={[
                                { value: 'mp4', label: 'MP4' },
                                { value: 'webm', label: 'WebM' },
                            ]}
                        />
                        <Select
                            label="Resolution"
                            value={selectedResolution}
                            onChange={(e) => setSelectedResolution(e.target.value)}
                            options={[
                                { value: '720p', label: '720p' },
                                { value: '1080p', label: '1080p' },
                                { value: '1440p', label: '1440p (2K)' },
                                { value: '2160p', label: '2160p (4K)' },
                                { value: 'best', label: 'Best Available' },
                            ]}
                        />
                    </div>

                    {/* Progress */}
                    {isDownloading && (
                        <div className="mb-4">
                            <ProgressBar progress={downloadProgress} label="Downloading" />
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                        <Button
                            variant="primary"
                            onClick={handleDownload}
                            isLoading={isDownloading}
                            disabled={isDownloading || video.status === 'failed'}
                            className="flex-1"
                        >
                            {isDownloading ? (
                                <>
                                    <Loader size={16} className="mr-2 animate-spin" />
                                    Downloading...
                                </>
                            ) : (
                                <>
                                    <Download size={16} className="mr-2" />
                                    Download
                                </>
                            )}
                        </Button>
                        <Button
                            variant="ghost"
                            onClick={onClose}
                            disabled={isDownloading}
                        >
                            Close
                        </Button>
                    </div>
                </div>
            </div>
        </Modal>
    );
};
