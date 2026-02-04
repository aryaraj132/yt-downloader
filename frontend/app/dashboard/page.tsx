'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useToast } from '@/components/ui/Toast';
import { Button } from '@/components/ui/Button';
import { VideoCard } from '@/components/VideoCard';
import { VideoDetailsModal } from '@/components/VideoDetailsModal';
import { videoService, type Video } from '@/services/videoService';
import { Loader, VideoOff } from 'lucide-react';

export default function DashboardPage() {
    const router = useRouter();
    const { isAuthenticated, user } = useAuthStore();
    const { showToast } = useToast();

    const [videos, setVideos] = useState<Video[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Pagination state
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);

    // Ref for infinite scroll observer
    const observerTarget = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/auth/login');
            return;
        }

        fetchVideos(1, true);
    }, [isAuthenticated, router]);

    // Infinite scroll observer
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && hasMore && !isLoadingMore && !isLoading) {
                    fetchVideos(page + 1, false);
                }
            },
            { threshold: 0.1 }
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => {
            if (observerTarget.current) {
                observer.unobserve(observerTarget.current);
            }
        };
    }, [hasMore, isLoadingMore, isLoading, page]);

    const fetchVideos = async (pageNum: number, isInitial: boolean = false) => {
        if (isInitial) {
            setIsLoading(true);
        } else {
            setIsLoadingMore(true);
        }

        try {
            const response = await videoService.listUserVideos(pageNum, 20);

            if (isInitial) {
                setVideos(response.videos);
            } else {
                setVideos(prev => [...prev, ...response.videos]);
            }

            setPage(pageNum);
            setHasMore(response.pagination.has_more);
        } catch (error: any) {
            showToast('Failed to load videos', 'error');
        } finally {
            setIsLoading(false);
            setIsLoadingMore(false);
        }
    };

    const handleCardClick = (videoId: string) => {
        const video = videos.find(v => v.video_id === videoId);
        if (video) {
            setSelectedVideo(video);
            setIsModalOpen(true);
        }
    };

    const handleDownloadClick = (videoId: string) => {
        const video = videos.find(v => v.video_id === videoId);
        if (video) {
            setSelectedVideo(video);
            setIsModalOpen(true);
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
                    <>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {videos.map((video) => (
                                <VideoCard
                                    key={video.video_id}
                                    video={video}
                                    onDownload={handleDownloadClick}
                                    onDelete={handleDelete}
                                    onShare={handleShare}
                                    onClick={handleCardClick}
                                />
                            ))}
                        </div>

                        {/* Infinite scroll trigger */}
                        {hasMore && (
                            <div ref={observerTarget} className="flex items-center justify-center py-8">
                                {isLoadingMore && (
                                    <Loader size={32} className="animate-spin text-primary-600" />
                                )}
                            </div>
                        )}

                        {!hasMore && videos.length > 0 && (
                            <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                                You've reached the end of your video library
                            </p>
                        )}
                    </>
                )}

                {/* Video Details Modal */}
                <VideoDetailsModal
                    video={selectedVideo}
                    isOpen={isModalOpen}
                    onClose={() => {
                        setIsModalOpen(false);
                        setSelectedVideo(null);
                    }}
                />
            </div>
        </div>
    );
}
