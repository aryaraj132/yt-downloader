'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useToast } from '@/components/ui/Toast';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { VideoCard } from '@/components/VideoCard';
import { videoService, type Video } from '@/services/videoService';
import { downloadFile } from '@/utils/downloadFile';
import { Loader, VideoOff } from 'lucide-react';

export default function DashboardPage() {
    const router = useRouter();
    const { isAuthenticated, user } = useAuthStore();
    const { showToast } = useToast();

    const [videos, setVideos] = useState<Video[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);
    const [selectedFormat, setSelectedFormat] = useState('mp4');
    const [selectedResolution, setSelectedResolution] = useState('1080p');
    const [isDownloading, setIsDownloading] = useState(false);

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/auth/login');
            return;
        }

        fetchVideos();
    }, [isAuthenticated, router]);

    const fetchVideos = async () => {
        setIsLoading(true);
        try {
            const response = await videoService.listUserVideos();
            setVideos(response.videos);
        } catch (error: any) {
            showToast('Failed to load videos', 'error');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDownloadClick = (videoId: string) => {
        const video = videos.find(v => v.video_id === videoId);
        if (video) {
            setSelectedVideo(video);
            setIsDownloadModalOpen(true);
        }
    };

    const handleDownload = async () => {
        if (!selectedVideo) return;

        setIsDownloading(true);
        try {
            const blob = await videoService.downloadVideo(selectedVideo.video_id, {
                format_preference: selectedFormat as any,
                resolution_preference: selectedResolution as any,
            });

            downloadFile(blob, `video_${selectedVideo.video_id}.${selectedFormat}`);
            showToast('Video downloaded successfully!', 'success');
            setIsDownloadModalOpen(false);
        } catch (error: any) {
            if (error.response?.status === 202) {
                showToast('Video is still processing. Please try again later.', 'info');
            } else {
                showToast('Download failed', 'error');
            }
        } finally {
            setIsDownloading(false);
        }
    };

    const handleDelete = async (videoId: string) => {
        if (!confirm('Are you sure you want to delete this video?')) {
            return;
        }

        try {
            // Note: Backend doesn't have a delete endpoint, so we'll just remove from UI
            setVideos(videos.filter(v => v.video_id !== videoId));
            showToast('Video removed', 'success');
        } catch (error: any) {
            showToast('Failed to delete video', 'error');
        }
    };

    const handleShare = (videoId: string) => {
        const video = videos.find(v => v.video_id === videoId);
        if (video) {
            navigator.clipboard.writeText(video.url);
            showToast('YouTube URL copied to clipboard!', 'success');
        }
    };

    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="container mx-auto px-4 py-12">
            <div className="max-w-7xl mx-auto">
                <div className="mb-8">
                    <h1 className="text-4xl font-bold mb-3 bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
                        My Videos
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        Manage your saved and downloaded videos
                    </p>
                </div>

                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader size={48} className="animate-spin text-primary-600" />
                    </div>
                ) : videos.length === 0 ? (
                    <div className="text-center py-20">
                        <VideoOff size={64} className="mx-auto mb-4 text-gray-400" />
                        <h2 className="text-2xl font-semibold mb-2 text-gray-900 dark:text-white">
                            No videos yet
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            Start downloading YouTube videos to see them here
                        </p>
                        <Button variant="primary" onClick={() => router.push('/download')}>
                            Download Your First Video
                        </Button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {videos.map((video) => (
                            <VideoCard
                                key={video.video_id}
                                video={video}
                                onDownload={handleDownloadClick}
                                onDelete={handleDelete}
                                onShare={handleShare}
                            />
                        ))}
                    </div>
                )}

                {/* Download Modal */}
                <Modal
                    isOpen={isDownloadModalOpen}
                    onClose={() => setIsDownloadModalOpen(false)}
                    title="Download Video"
                >
                    <div className="space-y-4">
                        <p className="text-gray-600 dark:text-gray-400">
                            Choose your preferred format and resolution for download
                        </p>

                        <div className="grid grid-cols-2 gap-4">
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

                        <div className="flex gap-3 pt-4">
                            <Button
                                variant="primary"
                                onClick={handleDownload}
                                isLoading={isDownloading}
                                className="flex-1"
                            >
                                Download
                            </Button>
                            <Button
                                variant="ghost"
                                onClick={() => setIsDownloadModalOpen(false)}
                                disabled={isDownloading}
                            >
                                Cancel
                            </Button>
                        </div>
                    </div>
                </Modal>
            </div>
        </div>
    );
}
