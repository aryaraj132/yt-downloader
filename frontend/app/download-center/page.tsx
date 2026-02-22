'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useToast } from '@/components/ui/Toast';
import { Button } from '@/components/ui/Button';
import { videoService, type RecentJob } from '@/services/videoService';
import {
    Loader,
    Download,
    Clock,
    CheckCircle,
    XCircle,
    RefreshCw,
    Film,
    Scissors,
    ExternalLink,
} from 'lucide-react';

export default function DownloadCenterPage() {
    const router = useRouter();
    const { isAuthenticated } = useAuthStore();
    const { showToast } = useToast();

    const [jobs, setJobs] = useState<RecentJob[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);

    const fetchJobs = useCallback(
        async (showRefreshIndicator = false) => {
            if (showRefreshIndicator) setIsRefreshing(true);
            else setIsLoading(true);

            try {
                const data = await videoService.getRecentJobs();
                setJobs(data.jobs);
            } catch (error: any) {
                showToast('Failed to load recent jobs', 'error');
            } finally {
                setIsLoading(false);
                setIsRefreshing(false);
            }
        },
        [showToast]
    );

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/auth/login');
            return;
        }
        fetchJobs();

        // Auto-refresh every 30 seconds
        const interval = setInterval(() => fetchJobs(true), 30000);
        return () => clearInterval(interval);
    }, [isAuthenticated, router, fetchJobs]);

    if (!isAuthenticated) return null;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'text-green-500';
            case 'processing':
                return 'text-yellow-500';
            case 'failed':
                return 'text-red-500';
            case 'queued':
            case 'pending':
                return 'text-blue-500';
            default:
                return 'text-gray-500';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'processing':
                return <Loader className="w-5 h-5 text-yellow-500 animate-spin" />;
            case 'failed':
                return <XCircle className="w-5 h-5 text-red-500" />;
            default:
                return <Clock className="w-5 h-5 text-blue-500" />;
        }
    };

    const formatTime = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString();
    };

    const formatDuration = (start?: number, end?: number) => {
        if (start == null || end == null) return null;
        const duration = end - start;
        const mins = Math.floor(duration / 60);
        const secs = duration % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const formatFileSize = (bytes?: number) => {
        if (!bytes) return null;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <div className="container mx-auto px-4 py-12">
            <div className="max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-4xl font-bold mb-3 bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
                            Download Center
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400">
                            Recent jobs from the past 24 hours
                        </p>
                    </div>
                    <Button
                        variant="outline"
                        onClick={() => fetchJobs(true)}
                        disabled={isRefreshing}
                    >
                        <RefreshCw
                            className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`}
                        />
                        Refresh
                    </Button>
                </div>

                {/* Job count */}
                {!isLoading && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        {jobs.length} job{jobs.length !== 1 ? 's' : ''} in the last 24 hours
                    </p>
                )}

                {/* Loading */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader size={48} className="animate-spin text-primary-600" />
                    </div>
                ) : jobs.length === 0 ? (
                    <div className="text-center py-20">
                        <Download size={64} className="mx-auto mb-4 text-gray-400" />
                        <h2 className="text-2xl font-semibold mb-2 text-gray-900 dark:text-white">
                            No recent jobs
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            Start downloading or encoding videos to see them here
                        </p>
                        <div className="flex gap-4 justify-center">
                            <Button variant="primary" onClick={() => router.push('/download')}>
                                Download Video
                            </Button>
                            <Button variant="outline" onClick={() => router.push('/encode')}>
                                Encode Video
                            </Button>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {jobs.map((job) => (
                            <div
                                key={job.job_id}
                                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:shadow-lg transition-shadow"
                            >
                                <div className="flex items-start justify-between">
                                    {/* Left side: Job info */}
                                    <div className="flex items-start gap-4 flex-1 min-w-0">
                                        {/* Job type icon */}
                                        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/20 flex items-center justify-center">
                                            {job.job_type === 'download' ? (
                                                <Scissors className="w-5 h-5 text-primary-600" />
                                            ) : (
                                                <Film className="w-5 h-5 text-primary-600" />
                                            )}
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            {/* Title */}
                                            <div className="flex items-center gap-2 mb-1">
                                                {getStatusIcon(job.status)}
                                                <span
                                                    className={`text-sm font-medium capitalize ${getStatusColor(
                                                        job.status
                                                    )}`}
                                                >
                                                    {job.status}
                                                </span>
                                                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 uppercase">
                                                    {job.job_type}
                                                </span>
                                            </div>

                                            {/* Details */}
                                            {job.job_type === 'download' && job.url && (
                                                <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                                                    {job.url}
                                                </p>
                                            )}
                                            {job.job_type === 'encode' && job.original_filename && (
                                                <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                                                    {job.original_filename}
                                                </p>
                                            )}

                                            {/* Meta info */}
                                            <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                                                <span className="flex items-center gap-1">
                                                    <Clock className="w-3 h-3" />
                                                    {formatTime(job.created_at)}
                                                </span>
                                                {job.start_time != null && job.end_time != null && (
                                                    <span>Duration: {formatDuration(job.start_time, job.end_time)}</span>
                                                )}
                                                {job.video_codec && (
                                                    <span>
                                                        Codec: {job.video_codec.toUpperCase()}
                                                        {job.quality_preset ? ` / ${job.quality_preset}` : ''}
                                                    </span>
                                                )}
                                                {job.file_size_bytes && (
                                                    <span>Size: {formatFileSize(job.file_size_bytes)}</span>
                                                )}
                                            </div>

                                            {/* Error message */}
                                            {job.error_message && (
                                                <p className="text-sm text-red-500 mt-2 truncate">
                                                    Error: {job.error_message}
                                                </p>
                                            )}
                                        </div>
                                    </div>

                                    {/* Right side: Download button */}
                                    {job.file_available && job.download_url && (
                                        <a
                                            href={job.download_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex-shrink-0 ml-4"
                                        >
                                            <Button variant="primary" size="sm">
                                                <Download className="w-4 h-4 mr-1" />
                                                Download
                                                <ExternalLink className="w-3 h-3 ml-1" />
                                            </Button>
                                        </a>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
