import { useState } from 'react';
import { authAPI } from '../services/api';

interface LoginPageProps {
    onLogin: (user: any, access: string, refresh: string) => void;
}

const QUICK_LOGINS = [
    { label: 'Admin', username: 'admin', password: 'admin123' },
    { label: 'Portfolio', username: 'portfolio', password: 'staff123' },
    { label: 'Collections', username: 'collections', password: 'staff123' },
    { label: 'Finance', username: 'finance', password: 'staff123' },
    { label: 'Underwriter', username: 'underwriter', password: 'staff123' },
];

export default function LoginPage({ onLogin }: LoginPageProps) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const res = await authAPI.login(username, password);
            const { access, refresh, user } = res.data;
            onLogin(user, access, refresh);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const fillQuick = (u: string, p: string) => {
        setUsername(u);
        setPassword(p);
        setError('');
    };

    return (
        <div className="login-page">
            <div className="login-card">
                <div className="login-logo">
                    <div className="login-logo-icon">IZ</div>
                    <div className="login-logo-text">Int<span>Zam</span> LMS</div>
                </div>

                <h1 className="login-title">Welcome back</h1>
                <p className="login-subtitle">Sign in to your admin dashboard</p>

                <div style={{ marginBottom: 20 }}>
                    <p style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Quick Access</p>
                    <div className="quick-access">
                        {QUICK_LOGINS.map(q => (
                            <button key={q.label} className="quick-btn" onClick={() => fillQuick(q.username, q.password)}>
                                {q.label}
                            </button>
                        ))}
                    </div>
                </div>

                {error && (
                    <div className="alert alert-error" style={{ marginBottom: 20 }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Username</label>
                        <input
                            id="username"
                            type="text"
                            className="form-control"
                            placeholder="Enter your username"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            required
                            autoFocus
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input
                            id="password"
                            type="password"
                            className="form-control"
                            placeholder="Enter your password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button
                        id="login-btn"
                        type="submit"
                        className="btn btn-primary w-full"
                        disabled={loading}
                        style={{ marginTop: 8, justifyContent: 'center', padding: '12px' }}
                    >
                        {loading ? <span className="loading-spinner"></span> : null}
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <p style={{ textAlign: 'center', marginTop: 24, fontSize: 13, color: 'var(--gray-400)' }}>
                    IntZam Micro Fin Limited © 2025
                </p>
            </div>
        </div>
    );
}
