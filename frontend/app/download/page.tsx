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
import { Download, Loader, AlertCircle, Clock, User, ExternalLink } from 'lucide-react';

const PUBLIC_MAX_DURATION = 40; // seconds

export default function DownloadPage() {
    const router = useRouter();
    const { showToast } = useToast();
    const { user, isAuthenticated } = useAuthStore();

    const [url, setUrl] = useState('');
    const [videoId, setVideoId] = useState<string | null>(null);
    const [startTime, setStartTime] = useState(0);
    const [endTime, setEndTime] = useState(40);
    const [resolutions, setResolutions] = useState<string[]>([]);
    const [selectedResolution, setSelectedResolution] = useState('1080p');
    const [selectedFormat, setSelectedFormat] = useState('mp4');
    const [isLoadingFormats, setIsLoadingFormats] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [savedVideoId, setSavedVideoId] = useState<string | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [publicToken, setPublicToken] = useState<string | null>(null);
    const [rateLimit, setRateLimit] = useState<{ used: number; limit: number; remaining: number; reset_at: string } | null>(null);

    // Fetch rate limit for guests
    useEffect(() => {
        const fetchRateLimit = async () => {
            if (!isAuthenticated) {
                try {
                    const limit = await videoService.checkRateLimit();
                    setRateLimit(limit);
                } catch (error) {
                    console.error('Failed to fetch rate limit:', error);
                }
            }
        };
        fetchRateLimit();
    }, [isAuthenticated]);

    useEffect(() => {
        const fetchPublicToken = async () => {
            if (isAuthenticated) {
                try {
                    const response = await authService.getPublicToken();
                    setPublicToken(response.token);
                } catch (error) {
                    console.error('Failed to get public token:', error);
                }
            }
        };
        fetchPublicToken();
    }, [isAuthenticated]);

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

    const handleDownloadAuthenticated = async () => {
        if (!publicToken) {
            showToast('Please wait, initializing...', 'info');
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
                    user_id: user!.id,
                },
                publicToken
            );

            setSavedVideoId(saveResponse.video_id);
            showToast('Video info saved! Queuing download...', 'success');

            // Step 2: Queue the download job
            const downloadResponse = await videoService.downloadVideo(saveResponse.video_id, {
                format_preference: selectedFormat as any,
                resolution_preference: selectedResolution as any,
            });

            // If already completed (cached), redirect to download directly
            if (downloadResponse.download_url && downloadResponse.status === 'completed') {
                window.open(downloadResponse.download_url, '_blank');
                showToast('Video ready! Opening download...', 'success');
                setIsDownloading(false);
                setDownloadProgress(0);
                return;
            }

            showToast('Job queued! Processing your video...', 'info');

            // Step 3: Poll for status
            const pollInterval = setInterval(async () => {
                try {
                    const status = await videoService.getVideoStatus(saveResponse.video_id);

                    if (status.progress) {
                        const phase = status.progress.current_phase;
                        const dlProgress = status.progress.download_progress || 0;
                        const encProgress = status.progress.encoding_progress || 0;
                        // Combine: downloading = 0-80%, encoding = 80-95%, uploading = 95-100%
                        let combined = 0;
                        if (phase === 'downloading') combined = dlProgress * 0.8;
                        else if (phase === 'encoding') combined = 80 + encProgress * 0.15;
                        else if (phase === 'uploading') combined = 95;
                        else if (phase === 'completed') combined = 100;
                        setDownloadProgress(Math.round(combined));
                    }

                    if (status.status === 'completed' && status.download_url) {
                        clearInterval(pollInterval);
                        window.open(status.download_url, '_blank');
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

            // Timeout after 10 minutes (longer since jobs go through queue)
            setTimeout(() => {
                clearInterval(pollInterval);
                if (isDownloading) {
                    showToast('Download is taking longer than expected. Check Download Center for status.', 'warning');
                    setIsDownloading(false);
                }
            }, 600000);

        } catch (error: any) {
            showToast(error.response?.data?.message || 'Download failed', 'error');
            setIsDownloading(false);
            setDownloadProgress(0);
        }
    };

    const handleDownloadGuest = async () => {
        setIsDownloading(true);
        try {
            // Call public API
            const response = await videoService.savePublicClip({
                url,
                start_time: startTime,
                end_time: endTime,
                format: selectedFormat,
                resolution: selectedResolution,
            });

            setJobId(response.job_id);
            setRateLimit({
                used: response.rate_limit.limit - response.rate_limit.remaining,
                limit: response.rate_limit.limit,
                remaining: response.rate_limit.remaining,
                reset_at: response.rate_limit.reset_at
            });
            showToast('Processing your clip...', 'info');

            // Poll for status
            const pollInterval = setInterval(async () => {
                try {
                    const status = await videoService.getPublicJobStatus(response.job_id);
                    setDownloadProgress(status.progress || 0);

                    if (status.file_ready) {
                        clearInterval(pollInterval);

                        // Download file
                        const blobUrl = await videoService.downloadPublicFile(response.job_id);

                        // Trigger download
                        const a = document.createElement('a');
                        a.href = blobUrl;
                        a.download = `clip.mp4`;

                        // Open in new tab if it's a remote URL (S3)
                        if (!blobUrl.startsWith('blob:')) {
                            a.target = '_blank';
                        }

                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);

                        if (blobUrl.startsWith('blob:')) {
                            window.URL.revokeObjectURL(blobUrl);
                        }

                        showToast('Clip downloaded successfully!', 'success');
                        setIsDownloading(false);
                        setDownloadProgress(0);
                        setJobId(null);
                    } else if (status.status === 'failed') {
                        clearInterval(pollInterval);
                        showToast(status.error_message || 'Processing failed', 'error');
                        setIsDownloading(false);
                        setDownloadProgress(0);
                        setJobId(null);
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    showToast('Error checking status', 'error');
                    setIsDownloading(false);
                    setDownloadProgress(0);
                    setJobId(null);
                }
            }, 2000);

            // Timeout after 3 minutes for guest
            setTimeout(() => {
                clearInterval(pollInterval);
                if (isDownloading) {
                    showToast('Processing timeout. Please try again.', 'warning');
                    setIsDownloading(false);
                }
            }, 180000);

        } catch (error: any) {
            const errorMsg = error.response?.data?.error || error.response?.data?.message || 'Download failed';
            showToast(errorMsg, 'error');
            setIsDownloading(false);
            setDownloadProgress(0);

            // Update rate limit if present in error response
            if (error.response?.data?.remaining !== undefined) {
                setRateLimit({
                    used: error.response.data.limit - error.response.data.remaining,
                    limit: error.response.data.limit,
                    remaining: error.response.data.remaining,
                    reset_at: error.response.data.reset_at
                });
            }
        }
    };

    const handleDownload = async () => {
        const duration = endTime - startTime;

        if (duration <= 0) {
            showToast('End time must be after start time', 'error');
            return;
        }

        // Check duration limits based on auth status
        const maxDuration = isAuthenticated ? 120 : PUBLIC_MAX_DURATION;
        if (duration > maxDuration) {
            showToast(`Duration cannot exceed ${maxDuration} seconds${!isAuthenticated ? ' for guest users' : ''}`, 'error');
            return;
        }

        if (isAuthenticated) {
            await handleDownloadAuthenticated();
        } else {
            await handleDownloadGuest();
        }
    };

    const duration = endTime - startTime;
    const maxDuration = isAuthenticated ? 120 : PUBLIC_MAX_DURATION;
    const timeError = duration > maxDuration ? `Duration cannot exceed ${maxDuration} seconds${!isAuthenticated ? ' (guest limit)' : ''}` : undefined;

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

                {/* Guest Mode Banner */}
                {!isAuthenticated && (
                    <div className="glass-effect rounded-xl p-4 mb-6 border-l-4 border-amber-500">
                        <div className="flex items-start gap-3">
                            <AlertCircle className="text-amber-500 flex-shrink-0 mt-0.5" size={20} />
                            <div className="flex-1">
                                <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                                    Guest Mode - Limited Access
                                </h3>
                                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                                    <li className="flex items-center gap-2">
                                        <Clock size={14} />
                                        Maximum clip duration: {PUBLIC_MAX_DURATION} seconds
                                    </li>
                                    {rateLimit && (
                                        <li className="flex items-center gap-2">
                                            <User size={14} />
                                            Rate limit: {rateLimit.remaining} of {rateLimit.limit} operations remaining today
                                        </li>
                                    )}
                                </ul>
                                <p className="text-sm mt-2">
                                    <a href="/auth/login" className="text-primary-600 hover:text-primary-700 font-medium underline">
                                        Sign in
                                    </a>
                                    {' '}for unlimited access (up to 120s clips, no daily limits)
                                </p>
                            </div>
                        </div>
                    </div>
                )}

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
                                src={`https://www.youtube.com/embed/${videoId}${startTime > 0 ? `?start=${startTime}` : ''}`}
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
                        maxDuration={maxDuration}
                    />

                    {/* Progress */}
                    {isDownloading && (
                        <div className="space-y-2">
                            <ProgressBar progress={downloadProgress} label={isAuthenticated ? "Downloading" : "Processing"} />
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
                        disabled={!videoId || isDownloading || !!timeError || isLoadingFormats || (rateLimit?.remaining === 0)}
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
                                Download Video {!isAuthenticated && `(${duration}s / ${PUBLIC_MAX_DURATION}s max)`}
                            </>
                        )}
                    </Button>

                    {!isAuthenticated && rateLimit?.remaining === 0 && (
                        <p className="text-sm text-center text-red-600 dark:text-red-400">
                            Rate limit exceeded. Please{' '}
                            <a href="/auth/login" className="underline font-medium">sign in</a>
                            {' '}for unlimited access or wait until tomorrow.
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
