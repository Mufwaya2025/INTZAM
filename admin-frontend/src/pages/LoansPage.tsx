import { useState, useEffect } from 'react';
import { loansAPI } from '../services/api';

const STATUS_BADGES: Record<string, string> = {
    PENDING_APPROVAL: 'badge-warning',
    APPROVED: 'badge-info',
    ACTIVE: 'badge-success',
    OVERDUE: 'badge-error',
    CLOSED: 'badge-gray',
    REJECTED: 'badge-error',
    WRITTEN_OFF: 'badge-gray',
};

interface LoansPageProps {
    userPermissions: string[];
}

export default function LoansPage({ userPermissions }: LoansPageProps) {
    const canDisburse = userPermissions.includes('disburse_loans');

    const [loans, setLoans] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedLoan, setSelectedLoan] = useState<any>(null);
    const [statusFilter, setStatusFilter] = useState(canDisburse ? 'APPROVED' : 'ACTIVE');
    const [repayAmount, setRepayAmount] = useState('');
    const [payoffQuote, setPayoffQuote] = useState<any>(null);
    const [rolloverInfo, setRolloverInfo] = useState<any>(null);
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => { loadLoans(); }, [statusFilter]);

    const loadLoans = async () => {
        setLoading(true);
        try {
            const res = await loansAPI.list({ status: statusFilter });
            setLoans(res.data.results || res.data);
        } catch {
            setLoans(MOCK_LOANS.filter(l => l.status === statusFilter));
        } finally {
            setLoading(false);
        }
    };

    const selectLoan = async (loan: any) => {
        setSelectedLoan(loan);
        setPayoffQuote(null);
        setRolloverInfo(null);
        setRepayAmount(String(loan.monthly_payment || ''));
    };

    const handleRepay = async () => {
        if (!selectedLoan || !repayAmount) return;
        setActionLoading(true);
        try {
            await loansAPI.repay(selectedLoan.id, Number(repayAmount));
            loadLoans();
            setSelectedLoan(null);
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error processing repayment');
        } finally {
            setActionLoading(false);
        }
    };

    const handleGetQuote = async () => {
        if (!selectedLoan) return;
        try {
            const res = await loansAPI.payoffQuote(selectedLoan.id);
            setPayoffQuote(res.data);
        } catch {
            setPayoffQuote({ principal_outstanding: 5000, early_termination_fee: 100, total_payoff_amount: 5100, interest_saved: 800 });
        }
    };

    const handleSettle = async () => {
        if (!selectedLoan) return;
        setActionLoading(true);
        try {
            await loansAPI.settle(selectedLoan.id);
            loadLoans();
            setSelectedLoan(null);
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error settling loan');
        } finally {
            setActionLoading(false);
        }
    };

    const handleRolloverCheck = async () => {
        if (!selectedLoan) return;
        try {
            const res = await loansAPI.rolloverEligibility(selectedLoan.id);
            setRolloverInfo(res.data);
        } catch {
            setRolloverInfo({ eligible: false, reason: 'Unable to check eligibility' });
        }
    };

    const handleRollover = async () => {
        if (!selectedLoan || !rolloverInfo?.eligible) return;
        setActionLoading(true);
        try {
            await loansAPI.rollover(selectedLoan.id, rolloverInfo.extension_days);
            loadLoans();
            setSelectedLoan(null);
            setRolloverInfo(null);
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error processing rollover');
        } finally {
            setActionLoading(false);
        }
    };

    const handleDisburse = async (loan = selectedLoan) => {
        if (!loan) return;
        setActionLoading(true);
        try {
            await loansAPI.disburse(loan.id);
            if (selectedLoan?.id === loan.id) {
                setSelectedLoan(null);
            }
            loadLoans();
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error disbursing loan');
        } finally {
            setActionLoading(false);
        }
    };

    const progress = selectedLoan
        ? Math.min(100, (Number(selectedLoan.repaid_amount) / Number(selectedLoan.total_repayable)) * 100)
        : 0;

    return (
        <div style={{ display: 'grid', gridTemplateColumns: selectedLoan ? '1fr 380px' : '1fr', gap: 20 }}>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Loan Servicing</h3>
                    <div className="flex gap-2">
                        {['APPROVED', 'ACTIVE', 'OVERDUE', 'CLOSED', 'PENDING_APPROVAL', 'REJECTED'].map(s => (
                            <button
                                key={s}
                                className={`btn btn-sm ${statusFilter === s ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setStatusFilter(s)}
                            >
                                {s.replace('_', ' ')}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="table-container">
                    {loading ? (
                        <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Loan #</th>
                                    <th>Client</th>
                                    <th>Amount</th>
                                    <th>Outstanding</th>
                                    <th>Progress</th>
                                    <th>Status</th>
                                    <th>Maturity</th>
                                    {statusFilter === 'APPROVED' && canDisburse && <th>Action</th>}
                                </tr>
                            </thead>
                            <tbody>
                                {loans.map(loan => {
                                    const prog = Math.min(100, (Number(loan.repaid_amount) / Number(loan.total_repayable)) * 100);
                                    return (
                                        <tr key={loan.id} onClick={() => selectLoan(loan)} style={{ cursor: 'pointer', background: selectedLoan?.id === loan.id ? 'var(--primary-50)' : '' }}>
                                            <td><strong>{loan.loan_number}</strong></td>
                                            <td>{loan.client_name || loan.client}</td>
                                            <td>ZMW {Number(loan.amount).toLocaleString()}</td>
                                            <td>ZMW {(Number(loan.total_repayable) - Number(loan.repaid_amount)).toLocaleString()}</td>
                                            <td style={{ width: 120 }}>
                                                <div className="progress-bar">
                                                    <div className="progress-fill" style={{ width: `${prog}%` }}></div>
                                                </div>
                                                <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 2 }}>{prog.toFixed(0)}%</div>
                                            </td>
                                            <td><span className={`badge ${STATUS_BADGES[loan.status] || 'badge-gray'}`}>{loan.status}</span></td>
                                            <td style={{ fontSize: 13 }}>{loan.maturity_date || '—'}</td>
                                            {statusFilter === 'APPROVED' && canDisburse && (
                                                <td>
                                                    <button
                                                        className="btn btn-success btn-sm"
                                                        onClick={(event) => {
                                                            event.stopPropagation();
                                                            handleDisburse(loan);
                                                        }}
                                                        disabled={actionLoading}
                                                    >
                                                        Disburse
                                                    </button>
                                                </td>
                                            )}
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {selectedLoan && (
                <div className="card" style={{ height: 'fit-content' }}>
                    <div className="card-header">
                        <h3 className="card-title">{selectedLoan.loan_number}</h3>
                        <button className="btn btn-secondary btn-icon" onClick={() => setSelectedLoan(null)}>✕</button>
                    </div>
                    <div className="card-body">
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 4 }}>Client</div>
                            <div style={{ fontWeight: 600 }}>{selectedLoan.client_name}</div>
                        </div>
                        {selectedLoan.status === 'APPROVED' && (
                            <div className="alert alert-info" style={{ marginBottom: 16 }}>
                                <span>
                                    This loan has been approved and is waiting for final disbursement.
                                    {selectedLoan.approved_by ? ` Approved by ${selectedLoan.approved_by}.` : ''}
                                </span>
                            </div>
                        )}
                        {selectedLoan.status === 'REJECTED' && (
                            <div className="alert alert-error" style={{ marginBottom: 16 }}>
                                <div>
                                    <div style={{ fontWeight: 600, marginBottom: 4 }}>Rejection Reason</div>
                                    <div style={{ fontSize: 13 }}>
                                        {selectedLoan.rejection_reason || 'No reason recorded.'}
                                    </div>
                                </div>
                            </div>
                        )}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>Principal</div>
                                <div style={{ fontWeight: 700, fontSize: 16 }}>ZMW {Number(selectedLoan.amount).toLocaleString()}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>Total Repayable</div>
                                <div style={{ fontWeight: 700, fontSize: 16 }}>ZMW {Number(selectedLoan.total_repayable).toLocaleString()}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>Repaid</div>
                                <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--success)' }}>ZMW {Number(selectedLoan.repaid_amount).toLocaleString()}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>Outstanding</div>
                                <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--error)' }}>
                                    ZMW {(Number(selectedLoan.total_repayable) - Number(selectedLoan.repaid_amount)).toLocaleString()}
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>Approved By</div>
                                <div style={{ fontWeight: 700, fontSize: 16 }}>{selectedLoan.approved_by || '—'}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>Disbursement Date</div>
                                <div style={{ fontWeight: 700, fontSize: 16 }}>{selectedLoan.disbursement_date || 'Pending'}</div>
                            </div>
                        </div>

                        <div style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 6 }}>Repayment Progress</div>
                            <div className="progress-bar" style={{ height: 10 }}>
                                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4 }}>{progress.toFixed(1)}% complete</div>
                        </div>

                        {selectedLoan.status === 'APPROVED' && canDisburse && (
                            <div style={{ borderTop: '1px solid var(--gray-100)', paddingTop: 16, marginBottom: 16 }}>
                                <div style={{ fontWeight: 600, marginBottom: 12 }}>Final Disbursement</div>
                                <button className="btn btn-success w-full" onClick={() => handleDisburse()} disabled={actionLoading}>
                                    {actionLoading ? <span className="loading-spinner"></span> : '💸'} Disburse Loan
                                </button>
                            </div>
                        )}

                        {selectedLoan.status === 'ACTIVE' && (
                            <>
                                <div style={{ borderTop: '1px solid var(--gray-100)', paddingTop: 16, marginBottom: 16 }}>
                                    <div style={{ fontWeight: 600, marginBottom: 12 }}>Post Repayment</div>
                                    <div className="form-group">
                                        <label className="form-label">Amount (ZMW)</label>
                                        <input className="form-control" type="number" value={repayAmount} onChange={e => setRepayAmount(e.target.value)} />
                                    </div>
                                    <button className="btn btn-success w-full" onClick={handleRepay} disabled={actionLoading}>
                                        {actionLoading ? <span className="loading-spinner"></span> : '💳'} Post Repayment
                                    </button>
                                </div>

                                <div style={{ borderTop: '1px solid var(--gray-100)', paddingTop: 16, marginBottom: 16 }}>
                                    <div style={{ fontWeight: 600, marginBottom: 12 }}>Early Settlement</div>
                                    {!payoffQuote ? (
                                        <button className="btn btn-secondary w-full" onClick={handleGetQuote}>Get Payoff Quote</button>
                                    ) : (
                                        <div>
                                            <div style={{ background: 'var(--gray-50)', borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 13 }}>
                                                <div className="flex justify-between mb-2"><span>Outstanding:</span><strong>ZMW {payoffQuote.principal_outstanding?.toLocaleString()}</strong></div>
                                                <div className="flex justify-between mb-2"><span>Early Fee:</span><strong>ZMW {payoffQuote.early_termination_fee?.toLocaleString()}</strong></div>
                                                <div className="flex justify-between" style={{ color: 'var(--primary-600)' }}><span>Total Payoff:</span><strong>ZMW {payoffQuote.total_payoff_amount?.toLocaleString()}</strong></div>
                                            </div>
                                            <button className="btn btn-danger w-full" onClick={handleSettle} disabled={actionLoading}>Settle Loan</button>
                                        </div>
                                    )}
                                </div>

                                <div style={{ borderTop: '1px solid var(--gray-100)', paddingTop: 16 }}>
                                    <div style={{ fontWeight: 600, marginBottom: 12 }}>Rollover</div>
                                    {!rolloverInfo ? (
                                        <button className="btn btn-secondary w-full" onClick={handleRolloverCheck}>Check Eligibility</button>
                                    ) : (
                                        <div>
                                            <div className={`alert ${rolloverInfo.eligible ? 'alert-success' : 'alert-error'}`}>
                                                {rolloverInfo.eligible ? `✓ Eligible - ${rolloverInfo.extension_days} days extension` : `✗ ${rolloverInfo.reason}`}
                                            </div>
                                            {rolloverInfo.eligible && (
                                                <button className="btn btn-primary w-full" onClick={handleRollover} disabled={actionLoading}>
                                                    Process Rollover
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

const MOCK_LOANS = [
    { id: 1, loan_number: 'LN123456', client_name: 'Alice Mwanza', amount: 10000, total_repayable: 12500, repaid_amount: 3500, monthly_payment: 1041.67, status: 'ACTIVE', maturity_date: '2025-12-01', term_months: 12 },
    { id: 2, loan_number: 'LN234567', client_name: 'Bob Tembo', amount: 5000, total_repayable: 5750, repaid_amount: 1000, monthly_payment: 958.33, status: 'ACTIVE', maturity_date: '2025-08-01', term_months: 6 },
    { id: 3, loan_number: 'LN345678', client_name: 'Eve Lungu', amount: 8000, total_repayable: 10800, repaid_amount: 2000, monthly_payment: 1200, status: 'OVERDUE', maturity_date: '2025-06-01', term_months: 9 },
    { id: 4, loan_number: 'LN456789', client_name: 'David Phiri', amount: 3000, total_repayable: 3750, repaid_amount: 0, monthly_payment: 1250, status: 'APPROVED', maturity_date: null, term_months: 3, approved_by: 'Underwriter One', disbursement_date: null },
];
