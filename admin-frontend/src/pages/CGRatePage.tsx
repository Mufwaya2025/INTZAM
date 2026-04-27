import { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { cgrateAPI } from '../services/api';

type CGRateTxn = {
    id: number;
    loan_number?: string;
    client_name?: string;
    transaction_type: string;
    name: string;
    phone_number: string;
    amount: string | number;
    reference: string;
    service: string;
    status: string;
    external_ref?: string;
    response_message?: string;
    created_at: string;
};

type PaginatedResponse<T> = {
    count?: number;
    next?: string | null;
    previous?: string | null;
    results?: T[];
};

const statusClass: Record<string, string> = {
    COMPLETED: 'badge-success',
    PENDING: 'badge-warning',
    PROCESSING: 'badge-info',
    FAILED: 'badge-error',
    ERROR: 'badge-error',
};

function money(value: number | string | null | undefined) {
    const num = Number(value || 0);
    return `ZMW ${Math.abs(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function listFromResponse<T>(data: T[] | PaginatedResponse<T>): T[] {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.results)) return data.results;
    return [];
}

export default function CGRatePage() {
    const [transactions, setTransactions] = useState<CGRateTxn[]>([]);
    const [balance, setBalance] = useState<number | null>(null);
    const [stats, setStats] = useState({ total_paid_today: 0, total_received_today: 0, paid_count: 0, received_count: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const loadData = async () => {
        setLoading(true);
        setError('');
        try {
            const [txRes, statsRes, balanceRes] = await Promise.allSettled([
                cgrateAPI.transactions(),
                cgrateAPI.stats(),
                cgrateAPI.balance(),
            ]);
            if (txRes.status === 'fulfilled') setTransactions(listFromResponse<CGRateTxn>(txRes.value.data));
            else throw txRes.reason;
            if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
            if (balanceRes.status === 'fulfilled') setBalance(balanceRes.value.data.balance);
            else setBalance(null);
        } catch (err: any) {
            setError(err.response?.data?.error || err.message || 'Failed to load CGRate transactions');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    const summary = useMemo(() => [
        { label: 'Current Balance', value: balance == null ? 'Unavailable' : money(balance), sub: 'CGRate account' },
        { label: 'Total Paid Today', value: money(stats.total_paid_today), sub: `${stats.paid_count} disbursement(s)` },
        { label: 'Total Received Today', value: money(stats.total_received_today), sub: `${stats.received_count} collection(s)` },
    ], [balance, stats]);

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1>CGRate Transactions</h1>
                    <p>Monitor mobile money disbursements and collections.</p>
                </div>
                <button className="btn btn-primary" onClick={loadData} disabled={loading}>
                    <RefreshCw size={16} /> Refresh
                </button>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

            <div className="stats-grid" style={{ marginBottom: 24 }}>
                {summary.map(item => (
                    <div className="stat-card" key={item.label}>
                        <div className="stat-content">
                            <div className="stat-label">{item.label}</div>
                            <div className="stat-value">{item.value}</div>
                            <div className="stat-change">{item.sub}</div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Recent Transactions</h2>
                </div>
                {loading ? (
                    <div className="empty-state">Loading CGRate transactions...</div>
                ) : (
                    <div className="table-container">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Customer</th>
                                    <th>Loan</th>
                                    <th>Type</th>
                                    <th>Amount</th>
                                    <th>Provider</th>
                                    <th>Reference</th>
                                    <th>Status</th>
                                    <th>External Ref</th>
                                </tr>
                            </thead>
                            <tbody>
                                {transactions.length === 0 ? (
                                    <tr><td colSpan={9} style={{ textAlign: 'center', padding: 32 }}>No CGRate transactions found.</td></tr>
                                ) : transactions.map(txn => (
                                    <tr key={txn.id}>
                                        <td>{new Date(txn.created_at).toLocaleString()}</td>
                                        <td>
                                            <div style={{ fontWeight: 600 }}>{txn.client_name || txn.name || 'N/A'}</div>
                                            <div style={{ color: 'var(--gray-500)', fontSize: 12 }}>{txn.phone_number}</div>
                                        </td>
                                        <td>{txn.loan_number || '-'}</td>
                                        <td>{txn.transaction_type}</td>
                                        <td style={{ color: Number(txn.amount) < 0 ? 'var(--error)' : 'var(--success)', fontWeight: 700 }}>
                                            {Number(txn.amount) < 0 ? '-' : '+'}{money(txn.amount)}
                                        </td>
                                        <td>{txn.service}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{txn.reference}</td>
                                        <td><span className={`badge ${statusClass[txn.status] || 'badge-gray'}`}>{txn.status}</span></td>
                                        <td>{txn.external_ref || txn.response_message || '-'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
