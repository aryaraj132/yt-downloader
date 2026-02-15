export const downloadFile = (file: Blob | { download_url: string }, filename: string) => {
    if ('download_url' in file) {
        const link = document.createElement('a');
        link.href = file.download_url;
        link.download = filename;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        return;
    }

    const url = window.URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
};
