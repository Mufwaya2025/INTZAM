import { useState, useEffect } from 'react';
import { loansAPI } from '../services/api';
import { Search, CreditCard } from 'lucide-react';
import type { Page } from '../components/AppShell';

interface LoansPageProps {
    navigate: (page: Page) => void;
}

const STATUS_FILTERS = ['ALL', 'ACTIVE', 'PENDING_APPROVAL', 'OVERDUE', 'CLOSED', 'REJECTED'] as const;
const STATUS_LABELS: Record<string, string> = {
    ALL: 'All',
    ACTIVE: 'Active',
    PENDING_APPROVAL: 'Pending',
    OVERDUE: 'Overdue',
    CLOSED: 'Closed',
    APPROVED: 'Approved',
    REJECTED: 'Rejected',
    WRITTEN_OFF: 'Written Off',
};

export default function LoansPage({ navigate }: LoansPageProps) {
    const [loans, setLoans] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>('ALL');
    const [search, setSearch] = useState('');

    useEffect(() => {
        loansAPI.list()
            .then(res => {
                const data = res.data?.results || res.data || [];
                setLoans(Array.isArray(data) ? data : []);
            })
            .catch(() => setLoans([]))
            .finally(() => setLoading(false));
    }, []);

    const filtered = loans.filter(l => {
        if (filter !== 'ALL' && l.status !== filter) return false;
        if (search) {
            const q = search.toLowerCase();
            return (
                l.loan_number?.toLowerCase().includes(q) ||
                l.product_name?.toLowerCase().includes(q) ||
                l.client_name?.toLowerCase().includes(q)
            );
        }
        return true;
    });

    const getStatusBadge = (status: string) => {
        const map: Record<string, string> = {
            ACTIVE: 'active',
            OVERDUE: 'overdue',
            PENDING_APPROVAL: 'pending',
            APPROVED: 'approved',
            CLOSED: 'closed',
            REJECTED: 'error',
            WRITTEN_OFF: 'error',
        };
        return map[status] || 'info';
    };

    return (
        <div>
            {/* Header */}
            <div className="page-header">
                <h1 className="page-header-title">My Loans</h1>
            </div>

            {/* Search */}
            <div style={{ padding: '12px 20px 0' }}>
                <div style={{ position: 'relative' }}>
                    <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--gray-400)' }} />
                    <input
                        type="text"
                        className="form-control"
                        placeholder="Search loans..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{ paddingLeft: 40 }}
                    />
                </div>
            </div>

            {/* Filters */}
            <div style={{ padding: '12px 20px', display: 'flex', gap: 8, overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                {STATUS_FILTERS.map(s => (
                    <button
                        key={s}
                        onClick={() => setFilter(s)}
                        style={{
                            padding: '6px 14px',
                            borderRadius: 'var(--radius-full)',
                            fontSize: 13,
                            fontWeight: 600,
                            border: 'none',
                            cursor: 'pointer',
                            whiteSpace: 'nowrap',
                            background: filter === s ? 'var(--primary-600)' : 'var(--gray-100)',
                            color: filter === s ? 'white' : 'var(--gray-600)',
                            transition: 'all 0.2s',
                            fontFamily: 'inherit',
                        }}
                    >
                        {STATUS_LABELS[s]}
                    </button>
                ))}
            </div>

            {/* Loans List */}
            <div className="section" style={{ paddingTop: 0 }}>
                {loading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="skeleton" style={{ width: '100%', height: 120, marginBottom: 12, borderRadius: 16 }}></div>
                    ))
                ) : filtered.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📋</div>
                        <h3>No Loans Found</h3>
                        <p>{filter !== 'ALL' ? `No ${STATUS_LABELS[filter].toLowerCase()} loans.` : 'Apply for your first loan today.'}</p>
                        <button className="btn btn-primary" style={{ margin: '0 auto', width: 'auto' }} onClick={() => navigate({ name: 'apply' })}>
                            <CreditCard size={16} />
                            Apply for Loan
                        </button>
                    </div>
                ) : (
                    filtered.map(loan => (
                        <div
                            key={loan.id}
                            className="loan-card"
                            onClick={() => navigate({ name: 'loan-detail', loanId: loan.id })}
                        >
                            <div className="loan-card-top">
                                <div>
                                    <div className="loan-card-title">{loan.product_name || 'Loan'}</div>
                                    <div className="loan-card-number">{loan.loan_number}</div>
                                </div>
                                <div>
                                    <div className="loan-card-amount">
                                        ZMW {parseFloat(
                                            (loan.status === 'ACTIVE' || loan.status === 'OVERDUE')
                                                ? (loan.outstanding_balance ?? loan.total_repayable ?? loan.amount)
                                                : loan.amount
                                        || 0).toLocaleString()}
                                    </div>
                                    <div className="loan-card-amount-label">
                                        {(loan.status === 'ACTIVE' || loan.status === 'OVERDUE') ? 'Outstanding' : 'Principal'}
                                    </div>
                                </div>
                            </div>
                            {(loan.status === 'ACTIVE' || loan.status === 'OVERDUE') && (
                                <>
                                    <div className="loan-progress">
                                        <div
                                            className={`loan-progress-fill ${loan.status === 'OVERDUE' ? 'overdue' : 'on-track'}`}
                                            style={{ width: `${Math.min(100, loan.repayment_progress || 0)}%` }}
                                        ></div>
                                    </div>
                                    <div className="loan-card-footer">
                                        <span className="loan-card-footer-left">
                                            {(loan.repayment_progress || 0).toFixed(0)}% repaid • ZMW {parseFloat(loan.outstanding_balance || 0).toLocaleString()} left
                                        </span>
                                        <span className={`badge badge-${getStatusBadge(loan.status)}`}>
                                            {STATUS_LABELS[loan.status] || loan.status}
                                        </span>
                                    </div>
                                </>
                            )}
                            {loan.status !== 'ACTIVE' && loan.status !== 'OVERDUE' && (
                                <div className="loan-card-footer" style={{ marginTop: 8 }}>
                                    <span className="loan-card-footer-left">
                                        {loan.term_months} months • {loan.interest_rate}% rate
                                    </span>
                                    <span className={`badge badge-${getStatusBadge(loan.status)}`}>
                                        {STATUS_LABELS[loan.status] || loan.status}
                                    </span>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
