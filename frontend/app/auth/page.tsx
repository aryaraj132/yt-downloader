'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/store/authStore';
import { motion } from 'framer-motion';

export default function AuthPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { login, isAuthenticated } = useAuthStore();
    const mode = searchParams.get('mode') || 'login'; // 'login' or 'register'

    useEffect(() => {
        // Redirect if already authenticated
        if (isAuthenticated) {
            router.push('/dashboard');
        }
    }, [isAuthenticated, router]);

    const handleGoogleLogin = async () => {
        setIsLoading(true);
        setError(null);

        try {
            const { auth_url } = await authService.initiateGoogleLogin();
            // Redirect to Google OAuth consent screen
            window.location.href = auth_url;
        } catch (err: any) {
            console.error('Google login error:', err);
            setError(err.response?.data?.error || 'Failed to initiate Google login');
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 px-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md"
            >
                <div className="bg-gray-800/50 backdrop-blur-xl border border-gray-700/50 rounded-2xl shadow-2xl p-8">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold text-white mb-2">
                            {mode === 'register' ? 'Create Account' : 'Welcome Back'}
                        </h1>
                        <p className="text-gray-400">
                            {mode === 'register'
                                ? 'Sign up with your Google account to get started'
                                : 'Sign in to access your video clips'}
                        </p>
                    </div>

                    {/* Error message */}
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg"
                        >
                            <p className="text-red-400 text-sm text-center">{error}</p>
                        </motion.div>
                    )}

                    {/* Google OAuth Button */}
                    <button
                        onClick={handleGoogleLogin}
                        disabled={isLoading}
                        className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white hover:bg-gray-100 text-gray-900 font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading ? (
                            <>
                                <div className="w-5 h-5 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" />
                                <span>Redirecting...</span>
                            </>
                        ) : (
                            <>
                                <svg className="w-5 h-5" viewBox="0 0 24 24">
                                    <path
                                        fill="#4285F4"
                                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                    />
                                    <path
                                        fill="#34A853"
                                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                    />
                                    <path
                                        fill="#FBBC05"
                                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                                    />
                                    <path
                                        fill="#EA4335"
                                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                                    />
                                </svg>
                                <span>Continue with Google</span>
                            </>
                        )}
                    </button>

                    {/* Toggle between login and register */}
                    <div className="mt-6 text-center">
                        <p className="text-gray-400 text-sm">
                            {mode === 'register' ? (
                                <>
                                    Already have an account?{' '}
                                    <button
                                        onClick={() => router.push('/auth?mode=login')}
                                        className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                                    >
                                        Sign in
                                    </button>
                                </>
                            ) : (
                                <>
                                    Don't have an account?{' '}
                                    <button
                                        onClick={() => router.push('/auth?mode=register')}
                                        className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                                    >
                                        Sign up
                                    </button>
                                </>
                            )}
                        </p>
                    </div>

                    {/* Features list */}
                    <div className="mt-8 pt-8 border-t border-gray-700/50">
                        <h3 className="text-white font-medium mb-4 text-center">What you'll get:</h3>
                        <ul className="space-y-3">
                            <li className="flex items-start gap-3 text-gray-300 text-sm">
                                <svg className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span>Access to YouTube livestream clipping</span>
                            </li>
                            <li className="flex start gap-3 text-gray-300 text-sm">
                                <svg className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span>Clip videos based on chat messages</span>
                            </li>
                            <li className="flex items-start gap-3 text-gray-300 text-sm">
                                <svg className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span>Manage and organize your clips</span>
                            </li>
                            <li className="flex items-start gap-3 text-gray-300 text-sm">
                                <svg className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span>Integration with Nightbot for easy clipping</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
