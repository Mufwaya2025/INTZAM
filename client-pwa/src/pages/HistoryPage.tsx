import { useState, useEffect } from 'react';
import { loansAPI } from '../services/api';
import type { Page } from '../components/AppShell';

interface HistoryPageProps {
    navigate: (page: Page) => void;
}

export default function HistoryPage({ navigate }: HistoryPageProps) {
    const [loans, setLoans] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'payments' | 'disbursements'>('all');

    useEffect(() => {
        loansAPI.list()
            .then(res => {
                const data = res.data?.results || res.data || [];
                setLoans(Array.isArray(data) ? data : []);
            })
            .catch(() => setLoans([]))
            .finally(() => setLoading(false));
    }, []);

    // Gather all transactions from all loans
    const allTransactions = loans.flatMap(loan =>
        (loan.transactions || []).map((tx: any) => ({
            ...tx,
            loan_number: loan.loan_number,
            loan_id: loan.id,
            product_name: loan.product_name,
        }))
    ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const filtered = allTransactions.filter(tx => {
        if (filter === 'payments') return tx.transaction_type === 'REPAYMENT';
        if (filter === 'disbursements') return tx.transaction_type === 'DISBURSEMENT';
        return true;
    });

    // Group by date
    const grouped: Record<string, typeof filtered> = {};
    filtered.forEach(tx => {
        const date = new Date(tx.created_at).toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
        });
        if (!grouped[date]) grouped[date] = [];
        grouped[date].push(tx);
    });

    const getIcon = (type: string) => {
        switch (type) {
            case 'REPAYMENT': return '💵';
            case 'DISBURSEMENT': return '📤';
            case 'PENALTY': return '⚠️';
            case 'SETTLEMENT': return '✅';
            case 'ROLLOVER_FEE': return '🔄';
            default: return '📋';
        }
    };

    const getIconClass = (type: string) => {
        switch (type) {
            case 'REPAYMENT': return 'credit';
            case 'DISBURSEMENT': return 'debit';
            case 'PENALTY': return 'pending';
            case 'SETTLEMENT': return 'credit';
            default: return 'debit';
        }
    };

    return (
        <div>
            {/* Header */}
            <div className="page-header">
                <h1 className="page-header-title">Transaction History</h1>
            </div>

            {/* Filters */}
            <div style={{ padding: '12px 20px', display: 'flex', gap: 8 }}>
                {([
                    ['all', 'All'],
                    ['payments', 'Payments'],
                    ['disbursements', 'Disbursements'],
                ] as const).map(([key, label]) => (
                    <button
                        key={key}
                        onClick={() => setFilter(key)}
                        style={{
                            padding: '6px 14px',
                            borderRadius: 'var(--radius-full)',
                            fontSize: 13,
                            fontWeight: 600,
                            border: 'none',
                            cursor: 'pointer',
                            background: filter === key ? 'var(--primary-600)' : 'var(--gray-100)',
                            color: filter === key ? 'white' : 'var(--gray-600)',
                            transition: 'all 0.2s',
                            fontFamily: 'inherit',
                        }}
                    >
                        {label}
                    </button>
                ))}
            </div>

            {/* Transactions */}
            <div className="section" style={{ paddingTop: 0 }}>
                {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="skeleton" style={{ width: '100%', height: 60, marginBottom: 8, borderRadius: 12 }}></div>
                    ))
                ) : Object.keys(grouped).length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📝</div>
                        <h3>No Transactions</h3>
                        <p>Your transaction history will appear here once you have active loans.</p>
                    </div>
                ) : (
                    Object.entries(grouped).map(([date, txs]) => (
                        <div key={date} style={{ marginBottom: 20 }}>
                            <div style={{
                                fontSize: 12,
                                fontWeight: 600,
                                color: 'var(--gray-400)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: 8,
                                paddingLeft: 4,
                            }}>
                                {date}
                            </div>
                            <div className="card">
                                <div className="card-body" style={{ padding: '4px 16px' }}>
                                    {txs.map((tx, i) => (
                                        <div
                                            className="tx-item"
                                            key={tx.id || i}
                                            onClick={() => navigate({ name: 'loan-detail', loanId: tx.loan_id })}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <div className={`tx-icon ${getIconClass(tx.transaction_type)}`}>
                                                {getIcon(tx.transaction_type)}
                                            </div>
                                            <div className="tx-details">
                                                <div className="tx-title">{tx.transaction_type?.replace(/_/g, ' ')}</div>
                                                <div className="tx-date">{tx.loan_number} • {tx.product_name || 'Loan'}</div>
                                            </div>
                                            <div className={`tx-amount ${getIconClass(tx.transaction_type)}`}>
                                                {tx.transaction_type === 'REPAYMENT' || tx.transaction_type === 'SETTLEMENT' ? '-' : '+'}
                                                ZMW {parseFloat(tx.amount || 0).toLocaleString()}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
