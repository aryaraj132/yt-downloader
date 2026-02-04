'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Copy, Check, Terminal, ExternalLink, Shield, Info } from 'lucide-react';
import { authService } from '../../services/authService';
import { useAuthStore } from '../../store/authStore';
import { Header } from '../../components/Header';
import { config } from '../../config';

export default function SetupPage() {
    const router = useRouter();
    const { user, isAuthenticated } = useAuthStore();
    const [loading, setLoading] = useState(true);
    const [token, setToken] = useState<string | null>(null);
    const [copiedToken, setCopiedToken] = useState(false);
    const [copiedCommand, setCopiedCommand] = useState(false);

    useEffect(() => {
        // Check auth status
        if (!isAuthenticated && !loading) {
            router.push('/auth');
            return;
        }

        const fetchToken = async () => {
            try {
                const data = await authService.getPublicToken();
                setToken(data.token);
            } catch (error) {
                console.error('Failed to fetch public token:', error);
            } finally {
                setLoading(false);
            }
        };

        if (isAuthenticated) {
            fetchToken();
        } else {
            // If not authenticated yet, wait for checkAuth or redirect
            // In a real app, useAuthStore probably handles initial load
            setLoading(false);
        }
    }, [isAuthenticated, router, loading]);

    const copyToClipboard = (text: string, setCopied: (val: boolean) => void) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const nightbotCommand = token
        ? `$(urlfetch ${config.siteUrl}/api/video/save/stream/${token}/$(chatid))`
        : 'Loading...';

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-950 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-950 text-white font-sans">
            <Header />

            <main className="container mx-auto px-4 py-8 max-w-4xl">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <div className="mb-8">
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent mb-2">
                            Setup & Configuration
                        </h1>
                        <p className="text-gray-400">
                            Configure your streaming tools to enable instant clipping directly from chat.
                        </p>
                    </div>

                    <div className="grid gap-6">
                        {/* Setup Card */}
                        <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden backdrop-blur-sm">
                            <div className="p-6 border-b border-gray-800 flex items-center gap-3">
                                <Terminal className="text-purple-400 w-6 h-6" />
                                <h2 className="text-xl font-semibold">Nightbot Integration</h2>
                            </div>

                            <div className="p-6 space-y-6">
                                <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 flex items-start gap-3">
                                    <Info className="text-purple-400 w-5 h-5 mt-0.5 flex-shrink-0" />
                                    <p className="text-sm text-purple-200">
                                        Add this command to Nightbot to let you or your moderators save clips by simply typing
                                        <span className="font-mono bg-purple-500/30 mx-1 px-1 rounded">!clip</span> in chat.
                                        Access token is generated automatically.
                                    </p>
                                </div>

                                {/* Command Box */}
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-gray-400 block">
                                        Command Response
                                    </label>
                                    <div className="relative group">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <span className="text-gray-500">$</span>
                                        </div>
                                        <input
                                            type="text"
                                            readOnly
                                            value={nightbotCommand}
                                            className="w-full bg-gray-950 border border-gray-800 text-gray-300 text-sm rounded-lg focus:ring-purple-500 focus:border-purple-500 block pl-8 pr-12 p-4 font-mono transition-colors"
                                        />
                                        <button
                                            onClick={() => copyToClipboard(nightbotCommand, setCopiedCommand)}
                                            className="absolute inset-y-0 right-0 flex items-center px-4 text-gray-500 hover:text-white transition-colors"
                                            title="Copy command"
                                        >
                                            {copiedCommand ? <Check className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
                                        </button>
                                    </div>
                                </div>

                                <div className="border-t border-gray-800 pt-6">
                                    <h3 className="font-medium text-white mb-4">How to set it up:</h3>
                                    <ol className="list-decimal list-inside space-y-3 text-gray-400 text-sm">
                                        <li>Go to your Nightbot dashboard (Commands &gt; Custom)</li>
                                        <li>Click <strong>Add Command</strong></li>
                                        <li>Command: <code className="text-purple-400">!clip</code></li>
                                        <li>Message: Paste the URL above</li>
                                        <li>Userlevel: <strong>Moderator</strong> (Recommended)</li>
                                        <li>Cooldown: <span className="text-gray-300">30 seconds</span></li>
                                    </ol>
                                </div>
                            </div>
                        </div>

                        {/* Public Token Card */}
                        <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden backdrop-blur-sm">
                            <div className="p-6 border-b border-gray-800 flex items-center gap-3">
                                <Shield className="text-blue-400 w-6 h-6" />
                                <h2 className="text-xl font-semibold">Your Public Token</h2>
                            </div>
                            <div className="p-6">
                                <p className="text-sm text-gray-400 mb-4">
                                    This token is used to identify your account for public API actions (like saving clips).
                                    Keep it secret if you don't want others filling up your storage!
                                </p>

                                <div className="relative">
                                    <input
                                        type="text"
                                        readOnly
                                        value={token || "Loading..."}
                                        className="w-full bg-gray-950 border border-gray-800 text-gray-400 text-sm rounded-lg p-3 font-mono pr-12"
                                    />
                                    <button
                                        onClick={() => token && copyToClipboard(token, setCopiedToken)}
                                        className="absolute inset-y-0 right-0 flex items-center px-4 text-gray-500 hover:text-white transition-colors"
                                    >
                                        {copiedToken ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </main>
        </div>
    );
}
