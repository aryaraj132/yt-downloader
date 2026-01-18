'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { TimeRangeSelector } from '@/components/TimeRangeSelector';
import { useToast } from '@/components/ui/Toast';
import { videoService } from '@/services/videoService';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/store/authStore';
import { extractYoutubeVideoId } from '@/utils/validation';
import { downloadFile } from '@/utils/downloadFile';
import { Download, Loader } from 'lucide-react';

export default function DownloadPage() {
    const router = useRouter();
    const { showToast } = useToast();
    const { user, isAuthenticated } = useAuthStore();

    const [url, setUrl] = useState('');
    const [videoId, setVideoId] = useState<string | null>(null);
    const [startTime, setStartTime] = useState(0);
    const [endTime, setEndTime] = useState(120);
    const [resolutions, setResolutions] = useState<string[]>([]);
    const [selectedResolution, setSelectedResolution] = useState('1080p');
    const [selectedFormat, setSelectedFormat] = useState('mp4');
    const [isLoadingFormats, setIsLoadingFormats] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [savedVideoId, setSavedVideoId] = useState<string | null>(null);
    const [publicToken, setPublicToken] = useState<string | null>(null);

    useEffect(() => {
        const fetchPublicToken = async () => {
            try {
                const response = await authService.getPublicToken();
                setPublicToken(response.token);
            } catch (error) {
                console.error('Failed to get public token:', error);
            }
        };
        fetchPublicToken();
    }, []);

    const handleUrlChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const newUrl = e.target.value;
        setUrl(newUrl);

        const vidId = extractYoutubeVideoId(newUrl);
        setVideoId(vidId);

        if (vidId) {
            setIsLoadingFormats(true);
            try {
                const response = await videoService.getAvailableResolutions(newUrl);
                setResolutions(response.resolutions);
                if (response.resolutions.length > 0) {
                    setSelectedResolution(response.resolutions[0]);
                }
            } catch (error: any) {
                showToast('Failed to fetch video formats', 'error');
            } finally {
                setIsLoadingFormats(false);
            }
        } else {
            setResolutions([]);
        }
    };

    const handleDownload = async () => {
        if (!user) {
            showToast('Please login to download videos', 'warning');
            router.push('/auth/login');
            return;
        }

        if (!publicToken) {
            showToast('Please wait, initializing...', 'info');
            return;
        }

        const duration = endTime - startTime;
        if (duration <= 0 || duration > 120) {
            showToast('Duration must be between 1 and 120 seconds', 'error');
            return;
        }

        setIsDownloading(true);
        try {
            // Step 1: Save video info
            const saveResponse = await videoService.saveVideoInfo(
                {
                    url,
                    start_time: startTime,
                    end_time: endTime,
                    user_id: user.id,
                },
                publicToken
            );

            setSavedVideoId(saveResponse.video_id);
            showToast('Video info saved! Starting download...', 'success');

            // Step 2: Poll for status and download
            const pollInterval = setInterval(async () => {
                try {
                    const status = await videoService.getVideoStatus(saveResponse.video_id);

                    if (status.progress) {
                        setDownloadProgress(status.progress.download_progress || 0);
                    }

                    if (status.status === 'completed') {
                        clearInterval(pollInterval);

                        // Download the video
                        const blob = await videoService.downloadVideo(saveResponse.video_id, {
                            format_preference: selectedFormat as any,
                            resolution_preference: selectedResolution as any,
                        });

                        downloadFile(blob, `video_${saveResponse.video_id}.${selectedFormat}`);
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
                    showToast('Download timeout. Check dashboard for status.', 'warning');
                    setIsDownloading(false);
                }
            }, 300000);

        } catch (error: any) {
            showToast(error.response?.data?.message || 'Download failed', 'error');
            setIsDownloading(false);
            setDownloadProgress(0);
        }
    };

    const timeError = endTime - startTime > 120 ? 'Duration cannot exceed 120 seconds' : undefined;

    return (
        <div className="container mx-auto px-4 py-12">
            <div className="max-w-4xl mx-auto">
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold mb-3 bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
                        Download YouTube Video
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        Download specific segments from YouTube videos with custom settings
                    </p>
                </div>

                <div className="glass-effect rounded-2xl p-8 space-y-6">
                    {/* URL Input */}
                    <Input
                        label="YouTube URL"
                        type="url"
                        placeholder="https://www.youtube.com/watch?v=..."
                        value={url}
                        onChange={handleUrlChange}
                        helperText="Enter a YouTube video URL to get started"
                    />

                    {/* Video Preview */}
                    {videoId && (
                        <div className="aspect-video rounded-xl overflow-hidden bg-gray-900">
                            <iframe
                                width="100%"
                                height="100%"
                                src={`https://www.youtube.com/embed/${videoId}`}
                                title="YouTube video player"
                                frameBorder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowFullScreen
                            />
                        </div>
                    )}

                    {/* Format and Resolution */}
                    {resolutions.length > 0 && (
                        <div className="grid grid-cols-2 gap-4">
                            <Select
                                label="Resolution"
                                value={selectedResolution}
                                onChange={(e) => setSelectedResolution(e.target.value)}
                                options={resolutions.map(res => ({ value: res, label: res }))}
                            />
                            <Select
                                label="Format"
                                value={selectedFormat}
                                onChange={(e) => setSelectedFormat(e.target.value)}
                                options={[
                                    { value: 'mp4', label: 'MP4' },
                                    { value: 'webm', label: 'WebM' },
                                ]}
                            />
                        </div>
                    )}

                    {/* Time Range Selector */}
                    <TimeRangeSelector
                        startTime={startTime}
                        endTime={endTime}
                        onStartTimeChange={setStartTime}
                        onEndTimeChange={setEndTime}
                        error={timeError}
                    />

                    {/* Progress */}
                    {isDownloading && (
                        <div className="space-y-2">
                            <ProgressBar progress={downloadProgress} label="Downloading" />
                            <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                                Please wait while we process your video...
                            </p>
                        </div>
                    )}

                    {/* Download Button */}
                    <Button
                        variant="primary"
                        size="lg"
                        className="w-full"
                        onClick={handleDownload}
                        disabled={!videoId || isDownloading || !isAuthenticated || !!timeError || isLoadingFormats}
                        isLoading={isDownloading}
                    >
                        {isDownloading ? (
                            <>
                                <Loader size={20} className="mr-2 animate-spin" />
                                Processing...
                            </>
                        ) : (
                            <>
                                <Download size={20} className="mr-2" />
                                Download Video
                            </>
                        )}
                    </Button>

                    {!isAuthenticated && (
                        <p className="text-sm text-center text-amber-600 dark:text-amber-400">
                            Please <a href="/auth/login" className="underline">login</a> to download videos
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
