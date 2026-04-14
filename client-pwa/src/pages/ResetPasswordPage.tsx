import { useState } from 'react';
import { passwordAPI } from '../services/api';
import { Eye, EyeOff } from 'lucide-react';

interface ResetPasswordPageProps {
    token: string;
    onSuccess: () => void;
}

export default function ResetPasswordPage({ token, onSuccess }: ResetPasswordPageProps) {
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (newPassword.length < 8) {
            setError('Password must be at least 8 characters.');
            return;
        }

        if (newPassword !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        setLoading(true);
        try {
            await passwordAPI.resetPassword(token, newPassword);
            setSuccess(true);
            setTimeout(() => {
                onSuccess();
            }, 2500);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Failed to reset password. The link may have expired.');
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
                <h2 className="login-form-title">Set New Password</h2>

                {success ? (
                    <div>
                        <div className="alert alert-success" style={{ marginBottom: 24 }}>
                            <span>✓</span> Password reset successfully! Redirecting to sign in...
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'center' }}>
                            <div className="loading-spinner" style={{ width: 28, height: 28 }}></div>
                        </div>
                    </div>
                ) : (
                    <>
                        {error && (
                            <div className="alert alert-error" style={{ marginBottom: 20 }}>
                                <span>⚠️</span> {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label className="form-label">New Password</label>
                                <div style={{ position: 'relative' }}>
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        className="form-control"
                                        placeholder="At least 8 characters"
                                        value={newPassword}
                                        onChange={e => setNewPassword(e.target.value)}
                                        required
                                        autoComplete="new-password"
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

                            <div className="form-group">
                                <label className="form-label">Confirm New Password</label>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    className="form-control"
                                    placeholder="Repeat your new password"
                                    value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                    required
                                    autoComplete="new-password"
                                />
                            </div>

                            <button
                                type="submit"
                                className="btn btn-primary btn-lg btn-block"
                                disabled={loading || !newPassword || !confirmPassword}
                                style={{ marginTop: 8 }}
                            >
                                {loading ? (
                                    <div className="loading-spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                                ) : 'Reset Password'}
                            </button>
                        </form>
                    </>
                )}
            </div>
        </div>
    );
}
