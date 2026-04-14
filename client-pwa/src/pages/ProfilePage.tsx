import { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { authAPI, clientsAPI } from '../services/api';
import {
    User, Mail, Shield, Key, LogOut, ChevronRight, Bell,
    Smartphone, HelpCircle, Star, Check, AlertCircle, FileText,
} from 'lucide-react';
import type { Page } from '../components/AppShell';

interface ProfilePageProps {
    navigate: (page: Page) => void;
}

export default function ProfilePage({ navigate }: ProfilePageProps) {
    const { user, logout } = useAuth();
    const [kycVerified, setKycVerified] = useState<boolean | null>(null);
    const [kycStatus, setKycStatus] = useState<string>('');

    useEffect(() => {
        clientsAPI.list().then(res => {
            const profile = Array.isArray(res.data) ? res.data[0] : res.data?.results?.[0];
            if (profile) {
                setKycVerified(profile.kyc_verified);
                setKycStatus(profile.vetting_status || '');
            }
        }).catch(() => {});
    }, []);
    const [showPasswordSheet, setShowPasswordSheet] = useState(false);
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [changingPassword, setChangingPassword] = useState(false);
    const [passwordError, setPasswordError] = useState('');
    const [passwordSuccess, setPasswordSuccess] = useState(false);
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

    const handleChangePassword = async () => {
        if (newPassword !== confirmPassword) {
            setPasswordError('Passwords do not match');
            return;
        }
        if (newPassword.length < 8) {
            setPasswordError('Password must be at least 8 characters');
            return;
        }
        setChangingPassword(true);
        setPasswordError('');
        try {
            await authAPI.changePassword(oldPassword, newPassword);
            setPasswordSuccess(true);
            setTimeout(() => {
                setShowPasswordSheet(false);
                setPasswordSuccess(false);
                setOldPassword('');
                setNewPassword('');
                setConfirmPassword('');
            }, 2000);
        } catch (err: any) {
            setPasswordError(err.response?.data?.error || 'Failed to change password');
        } finally {
            setChangingPassword(false);
        }
    };

    return (
        <div>
            {/* Header */}
            <div className="page-header">
                <h1 className="page-header-title">Profile</h1>
            </div>

            {/* Profile Card */}
            <div style={{ padding: '16px 20px' }}>
                <div className="card">
                    <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div style={{
                            width: 60,
                            height: 60,
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, var(--primary-500), var(--primary-700))',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontSize: 24,
                            fontWeight: 800,
                            flexShrink: 0,
                        }}>
                            {(user.name || user.username).charAt(0).toUpperCase()}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--gray-900)' }}>
                                {user.name || user.username}
                            </div>
                            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 2 }}>
                                {user.email}
                            </div>
                            <div style={{ marginTop: 6 }}>
                                <span className="badge badge-purple">{user.role}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* KYC Verification Status */}
            <div className="section" style={{ paddingTop: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingLeft: 4 }}>
                    Verification
                </div>
                <div
                    className="card"
                    onClick={() => navigate({ name: 'kyc' })}
                    style={{ cursor: 'pointer' }}
                >
                    <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                        <div style={{
                            width: 36, height: 36, borderRadius: 10,
                            background: kycVerified ? 'var(--success-light)' : kycStatus === 'PENDING' ? '#FEF3C7' : 'var(--error-light)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                        }}>
                            {kycVerified
                                ? <Check size={18} color="var(--success)" />
                                : kycStatus === 'PENDING'
                                    ? <AlertCircle size={18} color="#D97706" />
                                    : <FileText size={18} color="var(--error)" />
                            }
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--gray-800)' }}>Document Verification</div>
                            <div style={{ fontSize: 12, color: kycVerified ? 'var(--success)' : kycStatus === 'PENDING' ? '#D97706' : 'var(--error)', marginTop: 1, fontWeight: 500 }}>
                                {kycVerified ? 'Verified — you are eligible to borrow'
                                    : kycStatus === 'PENDING' ? 'Under review — awaiting approval'
                                    : kycStatus === 'REJECTED' ? 'Rejected — please re-submit documents'
                                    : 'Not submitted — upload documents to qualify'}
                            </div>
                        </div>
                        {!kycVerified && <ChevronRight size={18} color="var(--gray-400)" />}
                    </div>
                </div>
            </div>

            {/* Account Section */}
            <div className="section" style={{ paddingTop: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingLeft: 4 }}>
                    Account
                </div>
                <div className="card">
                    <div className="card-body" style={{ padding: 0 }}>
                        <MenuItem icon={<User size={18} />} label="Personal Info" subtitle={user.username} />
                        <MenuItem icon={<Mail size={18} />} label="Email" subtitle={user.email} />
                        <MenuItem icon={<Shield size={18} />} label="Role" subtitle={user.role} />
                        <MenuItem
                            icon={<Key size={18} />}
                            label="Change Password"
                            onClick={() => setShowPasswordSheet(true)}
                            showArrow
                        />
                    </div>
                </div>
            </div>

            {/* Settings Section */}
            <div className="section" style={{ paddingTop: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingLeft: 4 }}>
                    Settings
                </div>
                <div className="card">
                    <div className="card-body" style={{ padding: 0 }}>
                        <MenuItem icon={<Bell size={18} />} label="Notifications" subtitle="Enabled" />
                        <MenuItem icon={<Smartphone size={18} />} label="Install App" subtitle="Add to home screen" showArrow />
                        <MenuItem icon={<HelpCircle size={18} />} label="Help & Support" showArrow />
                        <MenuItem icon={<Star size={18} />} label="Rate Us" showArrow />
                    </div>
                </div>
            </div>

            {/* Logout */}
            <div className="section" style={{ paddingTop: 0 }}>
                <button
                    className="btn btn-danger btn-block"
                    onClick={() => setShowLogoutConfirm(true)}
                >
                    <LogOut size={18} />
                    Sign Out
                </button>
            </div>

            {/* App Version */}
            <div style={{ textAlign: 'center', padding: '8px 20px 32px', fontSize: 12, color: 'var(--gray-400)' }}>
                IntZam Loans v1.0.0
            </div>

            {/* Change Password Sheet */}
            {showPasswordSheet && (
                <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setShowPasswordSheet(false); }}>
                    <div className="bottom-sheet">
                        <div className="sheet-handle"></div>
                        <div className="sheet-header">
                            <span className="sheet-title">Change Password</span>
                            <button
                                onClick={() => setShowPasswordSheet(false)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray-400)', fontSize: 18 }}
                            >✕</button>
                        </div>
                        <div className="sheet-body">
                            {passwordSuccess ? (
                                <div style={{ textAlign: 'center', padding: 32 }}>
                                    <div style={{
                                        width: 56,
                                        height: 56,
                                        borderRadius: '50%',
                                        background: 'var(--success-light)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        margin: '0 auto 16px',
                                    }}>
                                        <Check size={28} color="var(--success)" />
                                    </div>
                                    <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--gray-900)' }}>Password Changed!</div>
                                </div>
                            ) : (
                                <>
                                    <div className="form-group">
                                        <label className="form-label">Current Password</label>
                                        <input
                                            type="password"
                                            className="form-control"
                                            value={oldPassword}
                                            onChange={e => setOldPassword(e.target.value)}
                                            placeholder="Enter current password"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">New Password</label>
                                        <input
                                            type="password"
                                            className="form-control"
                                            value={newPassword}
                                            onChange={e => setNewPassword(e.target.value)}
                                            placeholder="Enter new password"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Confirm New Password</label>
                                        <input
                                            type="password"
                                            className="form-control"
                                            value={confirmPassword}
                                            onChange={e => setConfirmPassword(e.target.value)}
                                            placeholder="Confirm new password"
                                        />
                                    </div>
                                    {passwordError && (
                                        <div className="alert alert-error">
                                            <AlertCircle size={14} />
                                            <span>{passwordError}</span>
                                        </div>
                                    )}
                                    <button
                                        className="btn btn-primary"
                                        onClick={handleChangePassword}
                                        disabled={changingPassword || !oldPassword || !newPassword || !confirmPassword}
                                    >
                                        {changingPassword ? (
                                            <div className="loading-spinner" style={{ width: 18, height: 18, borderWidth: 2 }}></div>
                                        ) : 'Update Password'}
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Logout Confirmation */}
            {showLogoutConfirm && (
                <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setShowLogoutConfirm(false); }}>
                    <div className="bottom-sheet" style={{ maxHeight: 'auto' }}>
                        <div className="sheet-handle"></div>
                        <div className="sheet-body" style={{ textAlign: 'center', padding: '32px 24px' }}>
                            <div style={{
                                width: 56,
                                height: 56,
                                borderRadius: '50%',
                                background: 'var(--error-light)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto 16px',
                            }}>
                                <LogOut size={24} color="var(--error)" />
                            </div>
                            <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 8 }}>
                                Sign Out?
                            </h3>
                            <p style={{ fontSize: 14, color: 'var(--gray-500)', marginBottom: 24 }}>
                                Are you sure you want to sign out of your account?
                            </p>
                            <div style={{ display: 'flex', gap: 10 }}>
                                <button className="btn btn-secondary" onClick={() => setShowLogoutConfirm(false)}>Cancel</button>
                                <button className="btn btn-danger" onClick={logout}>Sign Out</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function MenuItem({ icon, label, subtitle, onClick, showArrow }: {
    icon: React.ReactNode;
    label: string;
    subtitle?: string;
    onClick?: () => void;
    showArrow?: boolean;
}) {
    return (
        <div
            onClick={onClick}
            style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                padding: '14px 20px',
                borderBottom: '1px solid var(--gray-50)',
                cursor: onClick ? 'pointer' : 'default',
                transition: 'background 0.2s',
            }}
        >
            <div style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: 'var(--gray-50)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--gray-600)',
                flexShrink: 0,
            }}>
                {icon}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--gray-800)' }}>{label}</div>
                {subtitle && <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 1 }}>{subtitle}</div>}
            </div>
            {showArrow && <ChevronRight size={18} color="var(--gray-400)" />}
        </div>
    );
}
