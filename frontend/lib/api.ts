import axios from 'axios';

/**
 * Authenticated API client.
 *
 * All requests go through the Next.js API routes (e.g. /api/auth/*, /api/video/*)
 * which proxy them to the Flask backend. This keeps the backend URL private
 * and avoids CORS issues in the browser.
 *
 * The baseURL is `/api` so that service calls like `api.post('/auth/login', ...)`
 * resolve to `/api/auth/login` on the Next.js server.
 */
const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor: attach JWT token if available
api.interceptors.request.use((config) => {
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('auth_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

// Response interceptor: handle 401 (token expired / unauthorized)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Clear stored auth state on unauthorized response
            if (typeof window !== 'undefined') {
                localStorage.removeItem('auth_token');
                // Optionally redirect to login
                // window.location.href = '/auth/login';
            }
        }
        return Promise.reject(error);
    }
);

export default api;

/**
 * Public API client (no authentication).
 *
 * Used for public endpoints like /api/public/clip, /api/public/status, etc.
 * Same base URL but never attaches an auth token.
 */
export const publicApi = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});
