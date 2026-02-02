'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { useToast } from '@/components/ui/Toast';
import { encodeService } from '@/services/encodeService';
import { videoService } from '@/services/videoService';
import { useAuthStore } from '@/store/authStore';
import { downloadFile } from '@/utils/downloadFile';
import { Upload, Film, Download, FileVideo, AlertCircle, Clock, User } from 'lucide-react';

const PUBLIC_MAX_DURATION = 300; // 5 minutes in seconds

export default function EncodePage() {
    const router = useRouter();
    const { showToast } = useToast();
    const { isAuthenticated } = useAuthStore();

    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [fileDuration, setFileDuration] = useState<number | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [codec, setCodec] = useState<'h264' | 'h265' | 'av1'>('h264');
    const [quality, setQuality] = useState<'lossless' | 'high' | 'medium'>('high');
    const [isUploading, setIsUploading] = useState(false);
    const [isEncoding, setIsEncoding] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [encodeProgress, setEncodeProgress] = useState(0);
    const [encodeId, setEncodeId] = useState<string | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [supportedCodecs, setSupportedCodecs] = useState<any>(null);
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
        const fetchCodecs = async () => {
            try {
                const response = await encodeService.getSupportedCodecs();
                setSupportedCodecs(response.codecs);
            } catch (error) {
                console.error('Failed to fetch codecs:', error);
            }
        };
        fetchCodecs();
    }, []);

    // Check video duration when file is selected
    useEffect(() => {
        const checkDuration = async () => {
            if (selectedFile) {
                try {
                    const duration = await encodeService.getVideoDuration(selectedFile);
                    setFileDuration(duration);

                    // Validate for guest users
                    if (!isAuthenticated && duration > PUBLIC_MAX_DURATION) {
                        showToast(`Video duration (${Math.round(duration)}s) exceeds guest limit of ${PUBLIC_MAX_DURATION}s. Please sign in for longer videos.`, 'warning');
                    }
                } catch (error) {
                    console.error('Failed to get video duration:', error);
                    setFileDuration(null);
                }
            } else {
                setFileDuration(null);
            }
        };
        checkDuration();
    }, [selectedFile, isAuthenticated, showToast]);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            setSelectedFile(files[0]);
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            setSelectedFile(files[0]);
        }
    };

    const handleUploadAndEncodeAuthenticated = async () => {
        if (!selectedFile) return;

        setIsUploading(true);
        try {
            // Step 1: Upload file
            const uploadResponse = await encodeService.uploadVideo(selectedFile);
            setEncodeId(uploadResponse.encode_id);
            showToast('Upload successful! Starting encoding...', 'success');
            setIsUploading(false);
            setIsEncoding(true);

            // Step 2: Start encoding
            await encodeService.startEncoding(uploadResponse.encode_id, {
                video_codec: codec,
                quality_preset: quality,
            });

            // Step 3: Poll for encoding status
            const pollInterval = setInterval(async () => {
                try {
                    const status = await encodeService.getEncodingStatus(uploadResponse.encode_id);
                    setEncodeProgress(status.progress);

                    if (status.status === 'completed') {
                        clearInterval(pollInterval);
                        showToast('Encoding completed!', 'success');

                        // Download the encoded video
                        const blob = await encodeService.downloadEncodedVideo(uploadResponse.encode_id);
                        downloadFile(blob, `${selectedFile.name.replace(/\.[^/.]+$/, '')}_${codec}_${quality}.mp4`);

                        setIsEncoding(false);
                        setEncodeProgress(0);
                        setSelectedFile(null);
                        setEncodeId(null);
                    } else if (status.status === 'failed') {
                        clearInterval(pollInterval);
                        showToast(status.error_message || 'Encoding failed', 'error');
                        setIsEncoding(false);
                        setEncodeProgress(0);
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    showToast('Error checking encoding status', 'error');
                    setIsEncoding(false);
                    setEncodeProgress(0);
                }
            }, 2000);

            // Timeout after 10 minutes
            setTimeout(() => {
                clearInterval(pollInterval);
                if (isEncoding) {
                    showToast('Encoding timeout. Please check your dashboard.', 'warning');
                    setIsEncoding(false);
                }
            }, 600000);

        } catch (error: any) {
            showToast(error.response?.data?.message || 'Upload/encoding failed', 'error');
            setIsUploading(false);
            setIsEncoding(false);
            setUploadProgress(0);
            setEncodeProgress(0);
        }
    };

    const handleUploadAndEncodeGuest = async () => {
        if (!selectedFile) return;

        setIsEncoding(true);
        try {
            // Call public API
            const response = await encodeService.encodePublic(selectedFile, {
                video_codec: codec,
                quality_preset: quality,
            });

            setJobId(response.job_id);
            setRateLimit({
                used: response.rate_limit.limit - response.rate_limit.remaining,
                limit: response.rate_limit.limit,
                remaining: response.rate_limit.remaining,
                reset_at: response.rate_limit.reset_at
            });
            showToast('Encoding started...', 'info');

            // Poll for status
            const pollInterval = setInterval(async () => {
                try {
                    const status = await videoService.getPublicJobStatus(response.job_id);
                    setEncodeProgress(status.progress || 0);

                    if (status.file_ready) {
                        clearInterval(pollInterval);

                        // Download file
                        const blobUrl = await videoService.downloadPublicFile(response.job_id);

                        // Trigger download
                        const a = document.createElement('a');
                        a.href = blobUrl;
                        a.download = `${selectedFile.name.replace(/\.[^/.]+$/, '')}_encoded.mp4`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(blobUrl);

                        showToast('Video encoded and downloaded!', 'success');
                        setIsEncoding(false);
                        setEncodeProgress(0);
                        setSelectedFile(null);
                        setJobId(null);
                    } else if (status.status === 'failed') {
                        clearInterval(pollInterval);
                        showToast(status.error_message || 'Encoding failed', 'error');
                        setIsEncoding(false);
                        setEncodeProgress(0);
                        setJobId(null);
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    showToast('Error checking status', 'error');
                    setIsEncoding(false);
                    setEncodeProgress(0);
                    setJobId(null);
                }
            }, 3000); // Check every 3 seconds

            // Timeout after 15 minutes for encoding
            setTimeout(() => {
                clearInterval(pollInterval);
                if (isEncoding) {
                    showToast('Encoding timeout. Please try again.', 'warning');
                    setIsEncoding(false);
                }
            }, 900000);

        } catch (error: any) {
            const errorMsg = error.response?.data?.error || error.response?.data?.message || 'Encoding failed';
            showToast(errorMsg, 'error');
            setIsEncoding(false);
            setEncodeProgress(0);

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

    const handleUploadAndEncode = async () => {
        // Validate file duration for guests
        if (!isAuthenticated && fileDuration && fileDuration > PUBLIC_MAX_DURATION) {
            showToast(`Video duration exceeds guest limit of ${PUBLIC_MAX_DURATION}s. Please sign in.`, 'error');
            return;
        }

        if (isAuthenticated) {
            await handleUploadAndEncodeAuthenticated();
        } else {
            await handleUploadAndEncodeGuest();
        }
    };

    const isDurationExceeded = !isAuthenticated && fileDuration !== null && fileDuration > PUBLIC_MAX_DURATION;
    const isRateLimitExceeded = !isAuthenticated && rateLimit?.remaining === 0;

    return (
        <div className="container mx-auto px-4 py-12">
            <div className="max-w-4xl mx-auto">
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold mb-3 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                        Encode Video
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        Convert your videos to MP4 with premium codecs and quality settings
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
                                        Maximum video duration: {PUBLIC_MAX_DURATION / 60} minutes ({PUBLIC_MAX_DURATION}s)
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
                                    {' '}for unlimited access (longer videos, no daily limits)
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                <div className="glass-effect rounded-2xl p-8 space-y-6">
                    {/* File Upload Area */}
                    <div
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        className={`border-2 border-dashed rounded-xl p-12 text-center transition-all ${isDragging
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-gray-300 dark:border-gray-600 hover:border-primary-400'
                            }`}
                    >
                        {selectedFile ? (
                            <div className="space-y-3">
                                <FileVideo size={48} className="mx-auto text-primary-600" />
                                <div>
                                    <p className="text-lg font-medium text-gray-900 dark:text-white">{selectedFile.name}</p>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                                        {fileDuration && ` • ${Math.round(fileDuration)}s duration`}
                                    </p>
                                    {isDurationExceeded && (
                                        <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                                            ⚠️ Exceeds guest limit. Please sign in to encode this video.
                                        </p>
                                    )}
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setSelectedFile(null)}
                                    disabled={isUploading || isEncoding}
                                >
                                    Remove
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <Upload size={48} className="mx-auto text-gray-400" />
                                <div>
                                    <p className="text-lg font-medium text-gray-900 dark:text-white">
                                        Drag and drop your video here
                                    </p>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                        or click to browse (Max 500MB)
                                    </p>
                                </div>
                                <input
                                    type="file"
                                    accept="video/*"
                                    onChange={handleFileSelect}
                                    className="hidden"
                                    id="file-upload"
                                />
                                <label htmlFor="file-upload">
                                    <span className="inline-flex">
                                        <Button variant="outline" size="md">
                                            Select File
                                        </Button>
                                    </span>
                                </label>
                            </div>
                        )}
                    </div>

                    {/* Codec and Quality Selection */}
                    <div className="grid grid-cols-2 gap-4">
                        <Select
                            label="Video Codec"
                            value={codec}
                            onChange={(e) => setCodec(e.target.value as any)}
                            options={[
                                { value: 'h264', label: 'H.264 (Best Compatibility)' },
                                { value: 'h265', label: 'H.265 (Better Compression)' },
                                { value: 'av1', label: 'AV1 (Best Compression)' },
                            ]}
                            disabled={isUploading || isEncoding}
                        />
                        <Select
                            label="Quality Preset"
                            value={quality}
                            onChange={(e) => setQuality(e.target.value as any)}
                            options={[
                                { value: 'lossless', label: 'Lossless (Max Quality)' },
                                { value: 'high', label: 'High (Balanced)' },
                                { value: 'medium', label: 'Medium (Smaller Size)' },
                            ]}
                            disabled={isUploading || isEncoding}
                        />
                    </div>

                    {/* Progress */}
                    {isUploading && (
                        <div className="space-y-2">
                            <ProgressBar progress={uploadProgress} label="Uploading" />
                        </div>
                    )}

                    {isEncoding && (
                        <div className="space-y-2">
                            <ProgressBar progress={encodeProgress} label="Encoding" />
                            <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                                This may take a few minutes depending on file size...
                            </p>
                        </div>
                    )}

                    {/* Start Button */}
                    <Button
                        variant="secondary"
                        size="lg"
                        className="w-full"
                        onClick={handleUploadAndEncode}
                        disabled={!selectedFile || isUploading || isEncoding || isDurationExceeded || isRateLimitExceeded}
                        isLoading={isUploading || isEncoding}
                    >
                        {isUploading ? (
                            <>Uploading...</>
                        ) : isEncoding ? (
                            <>
                                <Film size={20} className="mr-2" />
                                Encoding...
                            </>
                        ) : (
                            <>
                                <Film size={20} className="mr-2" />
                                Start Encoding
                            </>
                        )}
                    </Button>

                    {isRateLimitExceeded && (
                        <p className="text-sm text-center text-red-600 dark:text-red-400">
                            Rate limit exceeded. Please{' '}
                            <a href="/auth/login" className="underline font-medium">sign in</a>
                            {' '}for unlimited access or wait until tomorrow.
                        </p>
                    )}

                    {/* Info */}
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                        <p className="text-sm text-blue-800 dark:text-blue-200">
                            <strong>Supported formats:</strong> MP4, AVI, MKV, MOV, FLV, WMV, WebM, M4V, MPG, MPEG, 3GP
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
