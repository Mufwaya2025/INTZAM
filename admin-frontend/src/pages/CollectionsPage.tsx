import { useState, useEffect } from 'react';
import { loansAPI } from '../services/api';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
interface CollectionsPageProps {
    userRole: string;
}



export default function CollectionsPage({ userRole: _userRole }: CollectionsPageProps) {
    const [loans, setLoans] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedLoan, setSelectedLoan] = useState<any>(null);
    const [activities, setActivities] = useState<any[]>([]);
    const [activityForm, setActivityForm] = useState({
        activity_type: 'CALL', notes: '', ptp_amount: '', ptp_date: '', outcome: 'CONTACTED'
    });
    const [actionLoading, setActionLoading] = useState(false);
    const [bucketFilter, setBucketFilter] = useState('ALL');

    useEffect(() => { loadOverdue(); }, []);

    const loadOverdue = async () => {
        try {
            const res = await loansAPI.list({ status: 'OVERDUE' });
            setLoans(res.data.results || res.data);
        } catch {
            setLoans(MOCK_OVERDUE);
        } finally {
            setLoading(false);
        }
    };

    const selectLoan = async (loan: any) => {
        setSelectedLoan(loan);
        try {
            const res = await loansAPI.activities(loan.id);
            setActivities(res.data.results || res.data);
        } catch {
            setActivities([]);
        }
    };

    const handleLogActivity = async () => {
        if (!selectedLoan) return;
        setActionLoading(true);
        try {
            await loansAPI.logActivity(selectedLoan.id, {
                ...activityForm,
                ptp_amount: activityForm.ptp_amount || null,
                ptp_date: activityForm.ptp_date || null,
            });
            const res = await loansAPI.activities(selectedLoan.id);
            setActivities(res.data.results || res.data);
            setActivityForm({ activity_type: 'CALL', notes: '', ptp_amount: '', ptp_date: '', outcome: 'CONTACTED' });
        } catch (e: any) {
            alert('Error logging activity');
        } finally {
            setActionLoading(false);
        }
    };

    const getBucket = (days: number) => {
        if (days <= 30) return '1-30';
        if (days <= 60) return '31-60';
        if (days <= 90) return '61-90';
        return '90+';
    };

    const getBucketColor = (days: number) => {
        if (days <= 30) return 'var(--warning)';
        if (days <= 60) return '#f97316';
        if (days <= 90) return 'var(--error)';
        return '#7f1d1d';
    };

    const filtered = bucketFilter === 'ALL' ? loans : loans.filter(l => getBucket(l.days_overdue || 0) === bucketFilter);

    const totalPAR = loans.reduce((sum, l) => sum + (Number(l.total_repayable) - Number(l.repaid_amount)), 0);

    return (
        <div>
            {/* Summary */}
            <div className="stat-grid" style={{ marginBottom: 20 }}>
                {[
                    { label: '1-30 Days', count: loans.filter(l => (l.days_overdue || 0) <= 30).length, color: 'var(--warning)' },
                    { label: '31-60 Days', count: loans.filter(l => (l.days_overdue || 0) > 30 && (l.days_overdue || 0) <= 60).length, color: '#f97316' },
                    { label: '61-90 Days', count: loans.filter(l => (l.days_overdue || 0) > 60 && (l.days_overdue || 0) <= 90).length, color: 'var(--error)' },
                    { label: '90+ Days', count: loans.filter(l => (l.days_overdue || 0) > 90).length, color: '#7f1d1d' },
                    { label: 'Total PAR', count: `ZMW ${(totalPAR / 1000).toFixed(0)}K`, color: 'var(--primary-600)' },
                ].map(b => (
                    <div key={b.label} className="stat-card">
                        <div className="stat-value" style={{ color: b.color }}>{b.count}</div>
                        <div className="stat-label">{b.label}</div>
                    </div>
                ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: selectedLoan ? '1fr 400px' : '1fr', gap: 20 }}>
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Overdue Loans ({filtered.length})</h3>
                        <div className="flex gap-2">
                            {['ALL', '1-30', '31-60', '61-90', '90+'].map(b => (
                                <button
                                    key={b}
                                    className={`btn btn-sm ${bucketFilter === b ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setBucketFilter(b)}
                                >
                                    {b}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="table-container">
                        {loading ? (
                            <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                        ) : filtered.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon">🎉</div>
                                <h3>No Overdue Loans</h3>
                                <p>All loans are current in this bucket.</p>
                            </div>
                        ) : (
                            <table>
                                <thead>
                                    <tr>
                                        <th>Loan #</th>
                                        <th>Client</th>
                                        <th>Outstanding</th>
                                        <th>Days Overdue</th>
                                        <th>PTP Status</th>
                                        <th>Phone</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.map(loan => (
                                        <tr key={loan.id} onClick={() => selectLoan(loan)} style={{ cursor: 'pointer', background: selectedLoan?.id === loan.id ? 'var(--primary-50)' : '' }}>
                                            <td><strong>{loan.loan_number}</strong></td>
                                            <td>
                                                <div style={{ fontWeight: 600 }}>{loan.client_name}</div>
                                            </td>
                                            <td style={{ color: 'var(--error)', fontWeight: 700 }}>
                                                ZMW {(Number(loan.total_repayable) - Number(loan.repaid_amount)).toLocaleString()}
                                            </td>
                                            <td>
                                                <span style={{
                                                    background: `${getBucketColor(loan.days_overdue || 0)}20`,
                                                    color: getBucketColor(loan.days_overdue || 0),
                                                    padding: '3px 10px',
                                                    borderRadius: 100,
                                                    fontSize: 12,
                                                    fontWeight: 700,
                                                }}>
                                                    {loan.days_overdue || 0} days
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`badge ${loan.ptp_status === 'ACTIVE' ? 'badge-info' : loan.ptp_status === 'FULFILLED' ? 'badge-success' : loan.ptp_status === 'BROKEN' ? 'badge-error' : 'badge-gray'}`}>
                                                    {loan.ptp_status || 'NONE'}
                                                </span>
                                            </td>
                                            <td style={{ fontSize: 13 }}>{loan.client_phone || '—'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>

                {selectedLoan && (
                    <div className="card" style={{ height: 'fit-content' }}>
                        <div className="card-header">
                            <h3 className="card-title">Collection Activity</h3>
                            <button className="btn btn-secondary btn-icon" onClick={() => setSelectedLoan(null)}>✕</button>
                        </div>
                        <div className="card-body">
                            <div style={{ background: 'var(--error-light)', borderRadius: 10, padding: 12, marginBottom: 16, fontSize: 13 }}>
                                <div style={{ fontWeight: 700, color: '#991b1b', marginBottom: 4 }}>{selectedLoan.client_name}</div>
                                <div style={{ color: '#991b1b' }}>
                                    Outstanding: <strong>ZMW {(Number(selectedLoan.total_repayable) - Number(selectedLoan.repaid_amount)).toLocaleString()}</strong>
                                    {' | '}{selectedLoan.days_overdue || 0} days overdue
                                </div>
                            </div>

                            {/* Log Activity Form */}
                            <div style={{ marginBottom: 16 }}>
                                <div style={{ fontWeight: 600, marginBottom: 12 }}>Log Activity</div>
                                <div className="form-group">
                                    <label className="form-label">Activity Type</label>
                                    <select className="form-control" value={activityForm.activity_type} onChange={e => setActivityForm({ ...activityForm, activity_type: e.target.value })}>
                                        <option value="CALL">Phone Call</option>
                                        <option value="SMS">SMS</option>
                                        <option value="EMAIL">Email</option>
                                        <option value="VISIT">Field Visit</option>
                                        <option value="LEGAL">Legal Notice</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Outcome</label>
                                    <select className="form-control" value={activityForm.outcome} onChange={e => setActivityForm({ ...activityForm, outcome: e.target.value })}>
                                        <option value="CONTACTED">Contacted</option>
                                        <option value="NO_ANSWER">No Answer</option>
                                        <option value="PROMISED_TO_PAY">Promised to Pay</option>
                                        <option value="REFUSED">Refused to Pay</option>
                                        <option value="PAID">Paid</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Notes</label>
                                    <textarea className="form-control" rows={3} value={activityForm.notes} onChange={e => setActivityForm({ ...activityForm, notes: e.target.value })} placeholder="Call notes..." />
                                </div>
                                {activityForm.outcome === 'PROMISED_TO_PAY' && (
                                    <div className="form-grid">
                                        <div className="form-group">
                                            <label className="form-label">PTP Amount (ZMW)</label>
                                            <input className="form-control" type="number" value={activityForm.ptp_amount} onChange={e => setActivityForm({ ...activityForm, ptp_amount: e.target.value })} />
                                        </div>
                                        <div className="form-group">
                                            <label className="form-label">PTP Date</label>
                                            <input className="form-control" type="date" value={activityForm.ptp_date} onChange={e => setActivityForm({ ...activityForm, ptp_date: e.target.value })} />
                                        </div>
                                    </div>
                                )}
                                <button className="btn btn-primary w-full" onClick={handleLogActivity} disabled={actionLoading || !activityForm.notes}>
                                    {actionLoading ? <span className="loading-spinner"></span> : '📝'} Log Activity
                                </button>
                            </div>

                            {/* Activity History */}
                            {activities.length > 0 && (
                                <div style={{ borderTop: '1px solid var(--gray-100)', paddingTop: 16 }}>
                                    <div style={{ fontWeight: 600, marginBottom: 12 }}>Activity History</div>
                                    <div style={{ maxHeight: 250, overflowY: 'auto' }}>
                                        {activities.map((a, i) => (
                                            <div key={i} style={{ padding: '10px 0', borderBottom: '1px solid var(--gray-100)', fontSize: 13 }}>
                                                <div className="flex justify-between">
                                                    <span className="badge badge-info">{a.activity_type}</span>
                                                    <span style={{ color: 'var(--gray-400)' }}>{a.created_at?.split('T')[0]}</span>
                                                </div>
                                                <div style={{ marginTop: 6, color: 'var(--gray-600)' }}>{a.notes}</div>
                                                {a.ptp_amount && (
                                                    <div style={{ marginTop: 4, color: 'var(--success)', fontWeight: 600 }}>
                                                        PTP: ZMW {a.ptp_amount} by {a.ptp_date}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

const MOCK_OVERDUE = [
    { id: 3, loan_number: 'LN345678', client_name: 'Eve Lungu', client_phone: '+260971000005', amount: 8000, total_repayable: 10800, repaid_amount: 2000, days_overdue: 45, ptp_status: 'ACTIVE' },
];
