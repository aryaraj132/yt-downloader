/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    images: {
        domains: ['i.ytimg.com', 'img.youtube.com'],
    },
}

module.exports = nextConfig
