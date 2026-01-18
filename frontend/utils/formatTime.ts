export const parseTimeToSeconds = (timeStr: string): number => {
    const parts = timeStr.split(':').map(Number);

    if (parts.length === 3) {
        // HH:MM:SS format
        const [hours, minutes, seconds] = parts;
        return hours * 3600 + minutes * 60 + seconds;
    } else if (parts.length === 2) {
        // MM:SS format
        const [minutes, seconds] = parts;
        return minutes * 60 + seconds;
    } else if (parts.length === 1) {
        // SS format
        return parts[0];
    }

    return 0;
};

export const formatSecondsToTime = (totalSeconds: number): string => {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};

export const validateTimeFormat = (timeStr: string): boolean => {
    const timeRegex = /^([0-9]{1,2}):([0-5][0-9]):([0-5][0-9])$/;
    return timeRegex.test(timeStr);
};
