import axios from 'axios';

const api = axios.create({
    baseURL: '/api/v1',
    headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('client_access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            const refreshToken = localStorage.getItem('client_refresh_token');
            if (refreshToken) {
                try {
                    const response = await axios.post('/api/v1/auth/refresh/', { refresh: refreshToken });
                    const { access } = response.data;
                    localStorage.setItem('client_access_token', access);
                    originalRequest.headers.Authorization = `Bearer ${access}`;
                    return api(originalRequest);
                } catch {
                    localStorage.removeItem('client_access_token');
                    localStorage.removeItem('client_refresh_token');
                    window.location.href = '/';
                }
            }
        }
        return Promise.reject(error);
    }
);

export default api;

// Password Reset API (unauthenticated)
export const passwordAPI = {
    forgotPassword: (email: string) => api.post('/auth/forgot-password/', { email }),
    resetPassword: (token: string, new_password: string) => api.post('/auth/reset-password/', { token, new_password }),
};

// Auth
export const authAPI = {
    login: (username: string, password: string) =>
        api.post('/auth/login/', { username, password }),
    register: (data: any) =>
        api.post('/auth/register/', data),
    logout: (refresh: string) =>
        api.post('/auth/logout/', { refresh }),
    me: () => api.get('/auth/me/'),
    changePassword: (old_password: string, new_password: string) =>
        api.post('/auth/change-password/', { old_password, new_password }),
};

// Client Profile
export const clientsAPI = {
    list: (params?: any) => api.get('/clients/', { params }),
    get: (id: number) => api.get(`/clients/${id}/`),
    create: (data: any) => api.post('/clients/', data),
    update: (id: number, data: any) => api.patch(`/clients/${id}/`, data),
};

// Products
export const productsAPI = {
    list: () => api.get('/products/'),
    get: (id: number) => api.get(`/products/${id}/`),
};

// Loans
export const loansAPI = {
    list: (params?: any) => api.get('/loans/', { params }),
    get: (id: number) => api.get(`/loans/${id}/`),
    create: (data: any) => api.post('/loans/', data),
    repay: (id: number, amount: number, notes?: string) =>
        api.post(`/loans/${id}/repay/`, { amount, notes }),
    payoffQuote: (id: number) => api.get(`/loans/${id}/payoff-quote/`),
    settle: (id: number, amount: number) => api.post(`/loans/${id}/settle/`, { amount }),
    rolloverEligibility: (id: number) => api.get(`/loans/${id}/rollover-eligibility/`),
    rollover: (id: number, extension_days: number) =>
        api.post(`/loans/${id}/rollover/`, { extension_days }),
    calculate: (data: any) => api.post('/calculator/', data),
    provideInfo: (id: number, response: string, files: File[] = []) => {
        const formData = new FormData();
        formData.append('response', response);
        files.forEach(f => formData.append('documents', f));
        return api.post(`/loans/${id}/provide-info/`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
};

// Dashboard
export const dashboardAPI = {
    stats: () => api.get('/dashboard/stats/'),
};

// KYC
export const kycAPI = {
    sections: () => api.get('/kyc/sections/'),
    submissions: () => api.get('/kyc/submissions/'),
    submit: (formData: FormData) => api.post('/kyc/submissions/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
};
