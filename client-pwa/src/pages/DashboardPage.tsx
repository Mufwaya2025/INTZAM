import { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { loansAPI, dashboardAPI, clientsAPI } from '../services/api';
import { CreditCard, Send, Calculator, Bell, ArrowRight, TrendingUp, Wallet, ShieldAlert } from 'lucide-react';
import type { Page } from '../components/AppShell';

interface DashboardPageProps {
    navigate: (page: Page) => void;
}

export default function DashboardPage({ navigate }: DashboardPageProps) {
    const { user } = useAuth();
    const [loans, setLoans] = useState<any[]>([]);
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [kycVerified, setKycVerified] = useState<boolean | null>(null);
    const [kycStatus, setKycStatus] = useState<string>('');

    useEffect(() => {
        Promise.all([
            loansAPI.list({ status: 'ACTIVE' }).catch(() => ({ data: { results: [] } })),
            dashboardAPI.stats().catch(() => ({ data: null })),
            clientsAPI.list().catch(() => ({ data: [] })),
        ]).then(([loansRes, statsRes, clientsRes]) => {
            const loansData = loansRes.data?.results || loansRes.data || [];
            setLoans(Array.isArray(loansData) ? loansData.slice(0, 3) : []);
            setStats(statsRes.data);

            const profile = Array.isArray(clientsRes.data) ? clientsRes.data[0] : clientsRes.data?.results?.[0];
            if (profile) {
                setKycVerified(profile.kyc_verified);
                setKycStatus(profile.vetting_status || '');
            }
        }).finally(() => setLoading(false));
    }, []);

    const totalOutstanding = loans.reduce((sum, l) => sum + (l.outstanding_balance || 0), 0);
    const totalRepaid = loans.reduce((sum, l) => sum + parseFloat(l.repaid_amount || 0), 0);
    const nextPayment = loans.length > 0 ? loans[0] : null;

    const greeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good Morning';
        if (hour < 17) return 'Good Afternoon';
        return 'Good Evening';
    };

    if (loading) {
        return (
            <div>
                <div className="hero-header">
                    <div className="hero-top">
                        <div>
                            <div className="skeleton" style={{ width: 120, height: 14, marginBottom: 8 }}></div>
                            <div className="skeleton" style={{ width: 160, height: 20 }}></div>
                        </div>
                        <div className="skeleton" style={{ width: 44, height: 44, borderRadius: '50%' }}></div>
                    </div>
                    <div className="skeleton" style={{ width: '100%', height: 120, borderRadius: 16 }}></div>
                </div>
                <div className="section">
                    <div className="skeleton" style={{ width: '100%', height: 80, marginBottom: 12 }}></div>
                    <div className="skeleton" style={{ width: '100%', height: 80 }}></div>
                </div>
            </div>
        );
    }

    return (
        <div>
            {/* Hero Header */}
            <div className="hero-header">
                <div className="hero-top">
                    <div>
                        <div className="hero-greeting">{greeting()}</div>
                        <div className="hero-name">{user.name || user.username} 👋</div>
                    </div>
                    <div className="hero-avatar" onClick={() => navigate({ name: 'profile' })}>
                        {(user.name || user.username).charAt(0).toUpperCase()}
                    </div>
                </div>

                <div className="hero-balance-card">
                    <div className="hero-balance-label">Total Outstanding</div>
                    <div className="hero-balance-amount">
                        ZMW {totalOutstanding.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </div>
                    <div className="hero-balance-row">
                        <div className="hero-balance-item">
                            <div className="hero-balance-item-label">Repaid</div>
                            <div className="hero-balance-item-value">
                                ZMW {totalRepaid.toLocaleString('en-US', { minimumFractionDigits: 0 })}
                            </div>
                        </div>
                        <div className="hero-balance-item">
                            <div className="hero-balance-item-label">Active Loans</div>
                            <div className="hero-balance-item-value">{loans.length}</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
                <div className="quick-action" onClick={() => navigate({ name: 'apply' })}>
                    <div className="quick-action-icon purple">
                        <CreditCard size={18} />
                    </div>
                    <div className="quick-action-label">Apply</div>
                </div>
                <div className="quick-action" onClick={() => {
                    if (nextPayment) navigate({ name: 'payment', loanId: nextPayment.id });
                    else navigate({ name: 'loans' });
                }}>
                    <div className="quick-action-icon green">
                        <Send size={18} />
                    </div>
                    <div className="quick-action-label">Pay</div>
                </div>
                <div className="quick-action" onClick={() => navigate({ name: 'loans' })}>
                    <div className="quick-action-icon amber">
                        <Calculator size={18} />
                    </div>
                    <div className="quick-action-label">My Loans</div>
                </div>
                <div className="quick-action" onClick={() => navigate({ name: 'history' })}>
                    <div className="quick-action-icon blue">
                        <Bell size={18} />
                    </div>
                    <div className="quick-action-label">History</div>
                </div>
            </div>

            {/* KYC Verification Banner */}
            {kycVerified === false && kycStatus !== 'PENDING' && (
                <div style={{ padding: '0 20px', marginBottom: 4 }}>
                    <div
                        onClick={() => navigate({ name: 'kyc' })}
                        style={{
                            background: kycStatus === 'REJECTED'
                                ? 'linear-gradient(135deg, #FEF2F2, #FEE2E2)'
                                : 'linear-gradient(135deg, #FFFBEB, #FEF3C7)',
                            border: `1.5px solid ${kycStatus === 'REJECTED' ? '#FECACA' : '#FDE68A'}`,
                            borderRadius: 14,
                            padding: '14px 16px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12,
                            cursor: 'pointer',
                        }}
                    >
                        <div style={{
                            width: 40, height: 40, borderRadius: 12, flexShrink: 0,
                            background: kycStatus === 'REJECTED' ? '#FEE2E2' : '#FEF3C7',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                            <ShieldAlert size={20} color={kycStatus === 'REJECTED' ? 'var(--error)' : '#D97706'} />
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--gray-900)' }}>
                                {kycStatus === 'REJECTED' ? 'Verification Rejected' : 'Verify Your Identity'}
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--gray-600)', marginTop: 1 }}>
                                {kycStatus === 'REJECTED'
                                    ? 'Your documents were rejected. Tap to re-submit.'
                                    : 'Upload your documents to qualify for loans'}
                            </div>
                        </div>
                        <ArrowRight size={18} color="var(--gray-400)" />
                    </div>
                </div>
            )}

            {kycVerified === false && kycStatus === 'PENDING' && (
                <div style={{ padding: '0 20px', marginBottom: 4 }}>
                    <div style={{
                        background: 'linear-gradient(135deg, #EFF6FF, #DBEAFE)',
                        border: '1.5px solid #BFDBFE',
                        borderRadius: 14,
                        padding: '14px 16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                    }}>
                        <div style={{
                            width: 40, height: 40, borderRadius: 12, flexShrink: 0,
                            background: '#DBEAFE',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                            <ShieldAlert size={20} color="#2563EB" />
                        </div>
                        <div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--gray-900)' }}>Verification Under Review</div>
                            <div style={{ fontSize: 12, color: 'var(--gray-600)', marginTop: 1 }}>Your documents are being reviewed by our team.</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Next Payment */}
            {nextPayment && (
                <div className="section" style={{ paddingBottom: 0 }}>
                    <div
                        className="card"
                        onClick={() => navigate({ name: 'payment', loanId: nextPayment.id })}
                        style={{ cursor: 'pointer' }}
                    >
                        <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                            <div style={{
                                width: 48,
                                height: 48,
                                borderRadius: 14,
                                background: 'linear-gradient(135deg, var(--primary-100), var(--primary-200))',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                            }}>
                                <Wallet size={22} color="var(--primary-600)" />
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 13, color: 'var(--gray-500)', fontWeight: 500 }}>Next Payment Due</div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--gray-900)' }}>
                                    ZMW {parseFloat(nextPayment.next_payment_due ?? nextPayment.monthly_payment ?? 0).toLocaleString()}
                                </div>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>
                                    {nextPayment.next_due_date ? `Due: ${nextPayment.next_due_date}` : nextPayment.loan_number}
                                </div>
                            </div>
                            <ArrowRight size={20} color="var(--gray-400)" />
                        </div>
                    </div>
                </div>
            )}

            {/* Active Loans */}
            <div className="section">
                <div className="section-header">
                    <h2 className="section-title">Active Loans</h2>
                    <span className="section-link" onClick={() => navigate({ name: 'loans' })}>
                        View All
                    </span>
                </div>

                {loans.length === 0 ? (
                    <div className="card" style={{ padding: '40px 20px', textAlign: 'center', background: 'rgba(255, 255, 255, 0.6)' }}>
                        <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'linear-gradient(135deg, var(--primary-50), var(--primary-100))', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', color: 'var(--primary-600)', boxShadow: 'var(--shadow-sm)' }}>
                            <Wallet size={28} />
                        </div>
                        <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 8 }}>No Active Loans</h3>
                        <p style={{ color: 'var(--gray-500)', fontSize: 14, marginBottom: 24, padding: '0 20px' }}>Apply for your first loan and get funded within minutes.</p>
                        <button className="btn btn-primary" style={{ margin: '0 auto', width: 'auto', padding: '12px 32px' }} onClick={() => navigate({ name: 'apply' })}>
                            <CreditCard size={18} />
                            Apply Now
                        </button>
                    </div>
                ) : (
                    loans.map(loan => (
                        <div
                            key={loan.id}
                            className="loan-card"
                            onClick={() => navigate({ name: 'loan-detail', loanId: loan.id })}
                        >
                            <div className="loan-card-top">
                                <div>
                                    <div className="loan-card-title">{loan.product_name || 'Personal Loan'}</div>
                                    <div className="loan-card-number">{loan.loan_number}</div>
                                </div>
                                <div>
                                    <div className="loan-card-amount">
                                        ZMW {parseFloat(loan.outstanding_balance || 0).toLocaleString()}
                                    </div>
                                    <div className="loan-card-amount-label">Outstanding</div>
                                </div>
                            </div>
                            <div className="loan-progress">
                                <div
                                    className={`loan-progress-fill ${loan.status === 'OVERDUE' ? 'overdue' : loan.days_overdue > 0 ? 'warning' : 'on-track'}`}
                                    style={{ width: `${Math.min(100, loan.repayment_progress || 0)}%` }}
                                ></div>
                            </div>
                            <div className="loan-card-footer">
                                <span className="loan-card-footer-left">
                                    {(loan.repayment_progress || 0).toFixed(0)}% repaid
                                </span>
                                <span className={`badge badge-${loan.status === 'ACTIVE' ? 'active' : loan.status === 'OVERDUE' ? 'overdue' : 'pending'}`}>
                                    {loan.status?.replace('_', ' ')}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Stats */}
            {stats && (
                <div className="section" style={{ paddingTop: 0 }}>
                    <div className="card">
                        <div className="card-body">
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                                <TrendingUp size={18} color="var(--primary-600)" />
                                <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--gray-900)' }}>Overview</span>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                <div style={{ background: 'var(--gray-50)', borderRadius: 10, padding: 12 }}>
                                    <div style={{ fontSize: 11, color: 'var(--gray-400)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>Total Borrowed</div>
                                    <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--gray-900)', marginTop: 4 }}>
                                        ZMW {(stats.total_portfolio / 1000 || 0).toFixed(0)}K
                                    </div>
                                </div>
                                <div style={{ background: 'var(--gray-50)', borderRadius: 10, padding: 12 }}>
                                    <div style={{ fontSize: 11, color: 'var(--gray-400)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>Total Repaid</div>
                                    <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--success)', marginTop: 4 }}>
                                        ZMW {(stats.total_repaid / 1000 || 0).toFixed(0)}K
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
