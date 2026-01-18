'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { useToast } from '@/components/ui/Toast';
import { encodeService } from '@/services/encodeService';
import { useAuthStore } from '@/store/authStore';
import { downloadFile } from '@/utils/downloadFile';
import { Upload, Film, Download, FileVideo } from 'lucide-react';

export default function EncodePage() {
    const router = useRouter();
    const { showToast } = useToast();
    const { isAuthenticated } = useAuthStore();

    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [codec, setCodec] = useState<'h264' | 'h265' | 'av1'>('h264');
    const [quality, setQuality] = useState<'lossless' | 'high' | 'medium'>('high');
    const [isUploading, setIsUploading] = useState(false);
    const [isEncoding, setIsEncoding] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [encodeProgress, setEncodeProgress] = useState(0);
    const [encodeId, setEncodeId] = useState<string | null>(null);
    const [supportedCodecs, setSupportedCodecs] = useState<any>(null);

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

    const handleUploadAndEncode = async () => {
        if (!isAuthenticated) {
            showToast('Please login to encode videos', 'warning');
            router.push('/auth/login');
            return;
        }

        if (!selectedFile) {
            showToast('Please select a video file', 'error');
            return;
        }

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
                                    </p>
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
                        disabled={!selectedFile || isUploading || isEncoding || !isAuthenticated}
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

                    {!isAuthenticated && (
                        <p className="text-sm text-center text-amber-600 dark:text-amber-400">
                            Please <a href="/auth/login" className="underline">login</a> to encode videos
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
