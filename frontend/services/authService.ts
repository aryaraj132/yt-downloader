import api from '@/lib/api';

export interface RegisterData {
    email: string;
    password: string;
}

export interface LoginData {
    email: string;
    password: string;
}

export interface ChangePasswordData {
    current_password: string;
    new_password: string;
}

export interface AuthResponse {
    message: string;
    token: string;
    user: {
        id: string;
        email: string;
    };
}

export interface UserResponse {
    user: {
        id: string;
        email: string;
    };
}

export const authService = {
    /**
     * @deprecated Use Google OAuth instead (initiateGoogleLogin)
     */
    async register(data: RegisterData): Promise<{ message: string; user_id: string }> {
        const response = await api.post('/auth/register', data);
        return response.data;
    },

    /**
     * @deprecated Use Google OAuth instead (initiateGoogleLogin)
     */
    async login(data: LoginData): Promise<AuthResponse> {
        const response = await api.post('/auth/login', data);
        return response.data;
    },

    async logout(): Promise<{ message: string }> {
        const response = await api.post('/auth/logout');
        return response.data;
    },

    /**
     * @deprecated Not applicable for OAuth users
     */
    async changePassword(data: ChangePasswordData): Promise<{ message: string }> {
        const response = await api.post('/auth/change-password', data);
        return response.data;
    },

    async getPublicToken(): Promise<{ token: string; expires_in: number }> {
        const response = await api.get('/auth/token/public');
        return response.data;
    },

    async getCurrentUser(): Promise<UserResponse> {
        const response = await api.get('/auth/me');
        return response.data;
    },

    async initiateGoogleLogin(): Promise<{ auth_url: string }> {
        const response = await api.get('/auth/google/login');
        return response.data;
    },

    async handleGoogleCallback(code: string): Promise<AuthResponse> {
        const response = await api.post('/auth/google/callback', { code });
        return response.data;
    },

    async refreshToken(): Promise<{ message: string; access_token: string }> {
        const response = await api.post('/auth/refresh-token');
        return response.data;
    },
};
