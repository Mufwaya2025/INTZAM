import axios from 'axios';

const api = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add JWT token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor to handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
                try {
                    const response = await axios.post('/api/v1/auth/refresh/', { refresh: refreshToken });
                    const { access } = response.data;
                    localStorage.setItem('access_token', access);
                    originalRequest.headers.Authorization = `Bearer ${access}`;
                    return api(originalRequest);
                } catch {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    window.location.href = '/login';
                }
            }
        }
        return Promise.reject(error);
    }
);

export default api;

// Auth API
export const authAPI = {
    login: (username: string, password: string) =>
        api.post('/auth/login/', { username, password }),
    logout: (refresh: string) =>
        api.post('/auth/logout/', { refresh }),
    me: () => api.get('/auth/me/'),
    getUsers: () => api.get('/auth/users/'),
    createUser: (data: any) => api.post('/auth/users/', data),
    updateUser: (id: number, data: any) => api.patch(`/auth/users/${id}/`, data),
    deleteUser: (id: number) => api.delete(`/auth/users/${id}/`),
};

// Clients API
export const clientsAPI = {
    list: (params?: any) => api.get('/clients/', { params }),
    get: (id: number) => api.get(`/clients/${id}/`),
    create: (data: any) => api.post('/clients/', data),
    update: (id: number, data: any) => api.patch(`/clients/${id}/`, data),
    delete: (id: number) => api.delete(`/clients/${id}/`),
};

// Qualified Base API
export const qualifiedBaseAPI = {
    list: (params?: any) => api.get('/qualified-base/', { params }),
    upload: (formData: FormData) => api.post('/qualified-base/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    create: (data: any) => api.post('/qualified-base/', data),
    eligibleClients: () => api.get('/qualified-base/eligible-clients/'),
    addFromClient: (data: { client_id: number; amount_qualified_for: number; reason: string; product_name?: string | null }) =>
        api.post('/qualified-base/from-client/', data),
};

// Products API
export const productsAPI = {
    list: () => api.get('/products/'),
    get: (id: number) => api.get(`/products/${id}/`),
    create: (data: any) => api.post('/products/', data),
    update: (id: number, data: any) => api.patch(`/products/${id}/`, data),
    delete: (id: number) => api.delete(`/products/${id}/`),
};

// Loans API
export const loansAPI = {
    list: (params?: any) => api.get('/loans/', { params }),
    get: (id: number) => api.get(`/loans/${id}/`),
    create: (data: any) => api.post('/loans/', data),
    approve: (id: number, comments?: string) => api.post(`/loans/${id}/approve/`, { comments }),
    reject: (id: number, reason: string) => api.post(`/loans/${id}/reject/`, { reason }),
    disburse: (id: number) => api.post(`/loans/${id}/disburse/`),
    returnToUnderwriter: (id: number, comments: string) => api.post(`/loans/${id}/return-to-underwriter/`, { comments }),
    repay: (id: number, amount: number, notes?: string) =>
        api.post(`/loans/${id}/repay/`, { amount, notes }),
    payoffQuote: (id: number) => api.get(`/loans/${id}/payoff-quote/`),
    settle: (id: number, amount: number) => api.post(`/loans/${id}/settle/`, { amount }),
    rolloverEligibility: (id: number) => api.get(`/loans/${id}/rollover-eligibility/`),
    rollover: (id: number, extension_days: number) =>
        api.post(`/loans/${id}/rollover/`, { extension_days }),
    writeOff: (id: number, reason: string) => api.post(`/loans/${id}/write-off/`, { reason }),
    requestInfo: (id: number, note: string) => api.post(`/loans/${id}/request-info/`, { note }),
    activities: (loanId: number) => api.get(`/loans/${loanId}/activities/`),
    logActivity: (loanId: number, data: any) => api.post(`/loans/${loanId}/activities/`, data),
    calculate: (data: any) => api.post('/calculator/', data),
};

export const cgrateAPI = {
    transactions: (params?: any) => api.get('/cgrate/transactions/', { params }),
    balance: () => api.get('/cgrate/balance/'),
    stats: () => api.get('/cgrate/stats/'),
    collect: (loanId: number, amount: number, notes?: string) =>
        api.post(`/loans/${loanId}/cgrate-collect/`, { amount, notes }),
    disburse: (loanId: number) => api.post(`/loans/${loanId}/cgrate-disburse/`),
};

// Accounting API
export const accountingAPI = {
    accounts: () => api.get('/accounting/accounts/'),
    createAccount: (data: any) => api.post('/accounting/accounts/', data),
    journal: () => api.get('/accounting/journal/'),
    createJournalEntry: (data: any) => api.post('/accounting/journal/', data),
    trialBalance: () => api.get('/accounting/trial-balance/'),
};

// Reports API
export const reportsAPI = {
    get: (type: string, params?: Record<string, any>) => api.get(`/reports/${type}/`, { params }),
    dashboardStats: () => api.get('/dashboard/stats/'),
};

// AI API
export const aiAPI = {
    analyze: (loanId: number) => api.post(`/ai/analyze/${loanId}/`),
};

// Settings API
export const settingsAPI = {
    getSmtp: () => api.get('/settings/smtp/'),
    saveSmtp: (data: any) => api.post('/settings/smtp/', data),
    testEmail: (email: string) => api.post('/settings/test-email/', { email }),
};

// Password reset API (unauthenticated)
export const passwordAPI = {
    forgotPassword: (email: string) => api.post('/auth/forgot-password/', { email }),
    resetPassword: (token: string, new_password: string) => api.post('/auth/reset-password/', { token, new_password }),
};

// KYC API
export const kycAPI = {
    sections: () => api.get('/kyc/sections/'),
    createSection: (data: any) => api.post('/kyc/sections/', data),
    updateSection: (id: number, data: any) => api.patch(`/kyc/sections/${id}/`, data),
    deleteSection: (id: number) => api.delete(`/kyc/sections/${id}/`),
    fields: () => api.get('/kyc/fields/'),
    createField: (data: any) => api.post('/kyc/fields/', data),
    updateField: (id: number, data: any) => api.patch(`/kyc/fields/${id}/`, data),
    deleteField: (id: number) => api.delete(`/kyc/fields/${id}/`),
    submissions: () => api.get('/kyc/submissions/'),
    getSubmission: (id: number) => api.get(`/kyc/submissions/${id}/`),
    reviewSubmission: (id: number, data: any) => api.patch(`/kyc/submissions/${id}/`, data),
};
