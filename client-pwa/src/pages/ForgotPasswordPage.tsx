import { useState } from 'react';
import { passwordAPI } from '../services/api';

interface ForgotPasswordPageProps {
    onBack: () => void;
}

export default function ForgotPasswordPage({ onBack }: ForgotPasswordPageProps) {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await passwordAPI.forgotPassword(email.trim());
            setSubmitted(true);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Something went wrong. Please try again.');
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
                <h2 className="login-form-title">Reset Password</h2>

                {submitted ? (
                    <div>
                        <div className="alert alert-success" style={{ marginBottom: 24 }}>
                            <span>✓</span> Check your email for a password reset link. It will expire in 1 hour.
                        </div>
                        <button
                            type="button"
                            className="btn btn-secondary btn-block"
                            onClick={onBack}
                        >
                            Back to Sign In
                        </button>
                    </div>
                ) : (
                    <>
                        <p style={{ color: 'var(--gray-500)', fontSize: 14, marginBottom: 20 }}>
                            Enter the email address associated with your account and we'll send you a reset link.
                        </p>

                        {error && (
                            <div className="alert alert-error" style={{ marginBottom: 20 }}>
                                <span>⚠️</span> {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label className="form-label">Email Address</label>
                                <input
                                    type="email"
                                    className="form-control"
                                    placeholder="Enter your email"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    required
                                    autoComplete="email"
                                />
                            </div>

                            <button
                                type="submit"
                                className="btn btn-primary btn-lg btn-block"
                                disabled={loading || !email.trim()}
                                style={{ marginTop: 8 }}
                            >
                                {loading ? (
                                    <div className="loading-spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                                ) : 'Send Reset Link'}
                            </button>
                        </form>

                        <div className="login-footer">
                            <p>
                                <span
                                    style={{ color: 'var(--primary-600)', cursor: 'pointer', fontWeight: 600 }}
                                    onClick={onBack}
                                >
                                    Back to Sign In
                                </span>
                            </p>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
