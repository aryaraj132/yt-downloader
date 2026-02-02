'use client';

import React, { useState } from 'react';
import { Input } from './ui/Input';
import { formatSecondsToTime, parseTimeToSeconds } from '@/utils/formatTime';

interface TimeRangeSelectorProps {
    startTime: number;
    endTime: number;
    onStartTimeChange: (seconds: number) => void;
    onEndTimeChange: (seconds: number) => void;
    error?: string;
    maxDuration: number;
}

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({
    startTime,
    endTime,
    onStartTimeChange,
    onEndTimeChange,
    error,
    maxDuration,
}) => {
    const [startTimeStr, setStartTimeStr] = useState(formatSecondsToTime(startTime));
    const [endTimeStr, setEndTimeStr] = useState(formatSecondsToTime(endTime));

    const handleStartTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setStartTimeStr(value);

        try {
            const seconds = parseTimeToSeconds(value);
            onStartTimeChange(seconds);
        } catch (err) {
            // Invalid format, don't update
        }
    };

    const handleEndTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setEndTimeStr(value);

        try {
            const seconds = parseTimeToSeconds(value);
            onEndTimeChange(seconds);
        } catch (err) {
            // Invalid format, don't update
        }
    };

    const duration = endTime - startTime;
    const isValidDuration = duration > 0 && duration <= maxDuration;

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <Input
                    label="Start Time (HH:MM:SS)"
                    type="text"
                    placeholder="00:00:00"
                    value={startTimeStr}
                    onChange={handleStartTimeChange}
                />
                <Input
                    label="End Time (HH:MM:SS)"
                    type="text"
                    placeholder="00:02:00"
                    value={endTimeStr}
                    onChange={handleEndTimeChange}
                    error={error}
                />
            </div>

            {duration > 0 && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Duration:</span>
                    <span className={`text-sm font-medium ${isValidDuration ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {duration} seconds {!isValidDuration && duration > maxDuration && `(Max ${maxDuration}s exceeded)`}
                    </span>
                </div>
            )}
        </div>
    );
};
