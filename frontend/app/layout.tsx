import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { ToastProvider } from "@/components/ui/Toast";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "YouTube Downloader - Download & Encode Videos",
    description: "Download YouTube video segments and encode videos with premium quality. Fast, secure, and easy to use.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body className={inter.className}>
                <Providers>
                    <ToastProvider>
                        <div className="min-h-screen flex flex-col bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
                            <Header />
                            <main className="flex-1">
                                {children}
                            </main>
                            <footer className="border-t border-gray-200 dark:border-gray-700 py-6 mt-12">
                                <div className="container mx-auto px-4 text-center text-sm text-gray-600 dark:text-gray-400">
                                    © 2026 YouTube Downloader. All rights reserved.
                                </div>
                            </footer>
                        </div>
                    </ToastProvider>
                </Providers>
            </body>
        </html>
    );
}
