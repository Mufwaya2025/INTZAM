import { useState } from 'react';
import { authAPI } from '../services/api';
import { Eye, EyeOff, LogIn } from 'lucide-react';

interface LoginPageProps {
    onLogin: (user: any, access: string, refresh: string) => void;
    onNavigateRegister: () => void;
    onForgotPassword: () => void;
}

export default function LoginPage({ onLogin, onNavigateRegister, onForgotPassword }: LoginPageProps) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const res = await authAPI.login(username, password);
            onLogin(res.data.user, res.data.access, res.data.refresh);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-header">
                <div className="login-logo">IZ</div>
                <h1 className="login-title">IntZam Loans</h1>
                <p className="login-subtitle">Your trusted partner in financial growth</p>
            </div>

            <div className="login-form-container">
                <h2 className="login-form-title">Sign In</h2>

                {error && (
                    <div className="alert alert-error" style={{ marginBottom: 20 }}>
                        <span>⚠️</span>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Phone Number or Email</label>
                        <input
                            id="login-username"
                            type="text"
                            className="form-control"
                            placeholder="Enter your phone or email"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            required
                            autoComplete="username"
                        />
                    </div>

                    <div className="form-group">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                            <label className="form-label" style={{ margin: 0 }}>Password</label>
                            <span
                                style={{ color: 'var(--primary-600)', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
                                onClick={onForgotPassword}
                            >
                                Forgot Password?
                            </span>
                        </div>
                        <div style={{ position: 'relative' }}>
                            <input
                                id="login-password"
                                type={showPassword ? 'text' : 'password'}
                                className="form-control"
                                placeholder="Enter your password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                                autoComplete="current-password"
                                style={{ paddingRight: 48 }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute',
                                    right: 12,
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    color: 'var(--gray-400)',
                                    padding: 4,
                                }}
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    <button
                        id="login-submit"
                        type="submit"
                        className="btn btn-primary btn-lg btn-block"
                        disabled={loading || !username || !password}
                        style={{ marginTop: 8 }}
                    >
                        {loading ? (
                            <div className="loading-spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                        ) : (
                            <>
                                <LogIn size={18} />
                                Sign In
                            </>
                        )}
                    </button>
                </form>

                <div className="login-footer">
                    <p>Don't have an account? <span style={{ color: 'var(--primary-600)', cursor: 'pointer', fontWeight: 600 }} onClick={onNavigateRegister}>Sign up</span></p>
                </div>
            </div>
        </div>
    );
}
