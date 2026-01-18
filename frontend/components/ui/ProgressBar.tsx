import React from 'react';
import { clsx } from 'clsx';

interface ProgressBarProps {
    progress: number;
    label?: string;
    showPercentage?: boolean;
    className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
    progress,
    label,
    showPercentage = true,
    className,
}) => {
    const clampedProgress = Math.min(100, Math.max(0, progress));

    return (
        <div className={clsx('w-full', className)}>
            {(label || showPercentage) && (
                <div className="flex justify-between mb-1">
                    {label && <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>}
                    {showPercentage && <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{Math.round(clampedProgress)}%</span>}
                </div>
            )}
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${clampedProgress}%` }}
                />
            </div>
        </div>
    );
};
