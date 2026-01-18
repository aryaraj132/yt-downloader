'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Download, Film, LayoutDashboard, Zap, Shield, Gauge } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export default function HomePage() {
    const { isAuthenticated } = useAuthStore();

    const features = [
        {
            icon: Download,
            title: 'YouTube Downloader',
            description: 'Download specific segments from YouTube videos with custom resolution and format preferences.',
            href: '/download',
            gradient: 'from-blue-500 to-cyan-500',
        },
        {
            icon: Film,
            title: 'Video Encoder',
            description: 'Encode videos to MP4 with H.264, H.265, or AV1 codecs with various quality presets.',
            href: '/encode',
            gradient: 'from-purple-500 to-pink-500',
        },
        {
            icon: LayoutDashboard,
            title: 'Manage Videos',
            description: 'Access your saved videos, download them anytime, and manage your library effortlessly.',
            href: isAuthenticated ? '/dashboard' : '/auth/login',
            gradient: 'from-orange-500 to-red-500',
        },
    ];

    const stats = [
        { icon: Zap, label: 'Lightning Fast', value: 'Processing' },
        { icon: Shield, label: 'Secure', value: 'Encryption' },
        { icon: Gauge, label: 'High Quality', value: 'Output' },
    ];

    return (
        <div className="container mx-auto px-4 py-12">
            {/* Hero Section */}
            <div className="text-center max-w-4xl mx-auto mb-16 animate-fade-in">
                <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary-600 via-accent-600 to-primary-600 bg-clip-text text-transparent leading-tight">
                    Download & Encode YouTube Videos
                </h1>
                <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 leading-relaxed">
                    Download specific segments from YouTube videos, encode videos with premium quality codecs,
                    and manage your video library - all in one place.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <Link href="/download">
                        <Button variant="primary" size="lg" className="w-full sm:w-auto">
                            <Download size={20} className="mr-2" />
                            Download Video
                        </Button>
                    </Link>
                    <Link href="/encode">
                        <Button variant="secondary" size="lg" className="w-full sm:w-auto">
                            <Film size={20} className="mr-2" />
                            Encode Video
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
                {stats.map((stat, index) => (
                    <div
                        key={index}
                        className="glass-effect rounded-xl p-6 text-center hover:scale-105 transition-transform duration-300"
                    >
                        <stat.icon size={40} className="mx-auto mb-3 text-primary-600 dark:text-primary-400" />
                        <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">{stat.value}</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">{stat.label}</div>
                    </div>
                ))}
            </div>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
                {features.map((feature, index) => (
                    <Link key={index} href={feature.href}>
                        <div className="glass-effect rounded-2xl p-8 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 cursor-pointer h-full">
                            <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-6`}>
                                <feature.icon size={32} className="text-white" />
                            </div>
                            <h3 className="text-2xl font-bold mb-3 text-gray-900 dark:text-white">
                                {feature.title}
                            </h3>
                            <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                                {feature.description}
                            </p>
                        </div>
                    </Link>
                ))}
            </div>

            {/* CTA Section */}
            <div className="glass-effect rounded-2xl p-12 text-center bg-gradient-to-r from-primary-500/10 to-accent-500/10">
                <h2 className="text-3xl md:text-4xl font-bold mb-4 text-gray-900 dark:text-white">
                    Ready to get started?
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
                    {isAuthenticated
                        ? 'Start downloading or encoding videos now!'
                        : 'Create an account to save your videos and access them anytime.'
                    }
                </p>
                {!isAuthenticated && (
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Link href="/auth/register">
                            <Button variant="primary" size="lg">
                                Create Account
                            </Button>
                        </Link>
                        <Link href="/auth/login">
                            <Button variant="outline" size="lg">
                                Sign In
                            </Button>
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}
