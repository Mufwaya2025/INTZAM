import { useState, useEffect } from 'react';
import { loansAPI } from '../services/api';
import { ArrowLeft, Send } from 'lucide-react';
import type { Page } from '../components/AppShell';


const FREQ_LABEL: Record<string, string> = {
    WEEKLY: 'Weekly Payment',
    BIWEEKLY: 'Bi-Weekly Payment',
    MONTHLY: 'Monthly Payment',
};

const FREQ_DISPLAY: Record<string, string> = {
    WEEKLY: 'Weekly',
    BIWEEKLY: 'Every 2 Weeks',
    MONTHLY: 'Monthly',
};

interface LoanDetailPageProps {
    loanId: number;
    navigate: (page: Page) => void;
}

export default function LoanDetailPage({ loanId, navigate }: LoanDetailPageProps) {
    const [loan, setLoan] = useState<any>(null);
    const [transactions, setTransactions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'details' | 'transactions'>('details');
    const [infoResponse, setInfoResponse] = useState('');
    const [infoFiles, setInfoFiles] = useState<File[]>([]);
    const [infoSubmitting, setInfoSubmitting] = useState(false);
    const [infoSubmitted, setInfoSubmitted] = useState(false);

    useEffect(() => {
        Promise.all([
            loansAPI.get(loanId).catch(() => ({ data: null })),
        ]).then(([loanRes]) => {
            setLoan(loanRes.data);
            // Try to get transactions from the loan data
            if (loanRes.data?.transactions) {
                setTransactions(loanRes.data.transactions);
            }
        }).finally(() => setLoading(false));
    }, [loanId]);

    if (loading) {
        return (
            <div>
                <div className="page-header">
                    <div className="page-header-back" onClick={() => navigate({ name: 'loans' })}>
                        <ArrowLeft size={20} />
                    </div>
                    <span className="page-header-title">Loan Details</span>
                </div>
                <div className="page-loader">
                    <div className="loading-spinner" style={{ width: 32, height: 32 }}></div>
                </div>
            </div>
        );
    }

    if (!loan) {
        return (
            <div>
                <div className="page-header">
                    <div className="page-header-back" onClick={() => navigate({ name: 'loans' })}>
                        <ArrowLeft size={20} />
                    </div>
                    <span className="page-header-title">Loan Details</span>
                </div>
                <div className="empty-state">
                    <div className="empty-state-icon">❌</div>
                    <h3>Loan Not Found</h3>
                    <p>This loan could not be loaded.</p>
                </div>
            </div>
        );
    }

    const handleProvideInfo = async () => {
        if (!infoResponse.trim() && infoFiles.length === 0) return;
        setInfoSubmitting(true);
        try {
            const res = await loansAPI.provideInfo(loan.id, infoResponse, infoFiles);
            setLoan(res.data);
            setInfoSubmitted(true);
            setInfoResponse('');
            setInfoFiles([]);
        } catch (e: any) {
            alert(e.response?.data?.error || 'Failed to submit response');
        } finally {
            setInfoSubmitting(false);
        }
    };

    const progress = Math.min(100, loan.repayment_progress || 0);
    const outstanding = parseFloat(loan.outstanding_balance || 0);
    const isActive = loan.status === 'ACTIVE' || loan.status === 'OVERDUE';

    // Build chronological transaction ledger with running balance
    const totalRepayable = parseFloat(loan.total_repayable || 0);
    const totalInterest = totalRepayable - parseFloat(loan.amount || 0);
    const sortedTxs = [...transactions].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
    let runningBalance = 0;
    const ledger = sortedTxs.map(tx => {
        const amt = parseFloat(tx.amount || 0);
        if (tx.transaction_type === 'DISBURSEMENT') {
            runningBalance = totalRepayable;
        } else if (['REPAYMENT', 'SETTLEMENT', 'WRITE_OFF', 'RECOVERY'].includes(tx.transaction_type)) {
            runningBalance -= amt;
        } else if (['PENALTY', 'ROLLOVER_FEE'].includes(tx.transaction_type)) {
            runningBalance += amt;
        }
        return { ...tx, _balance: Math.max(0, runningBalance) };
    });

    const TX_META: Record<string, { icon: string; label: string; color: 'credit' | 'debit' | 'pending'; sign: string }> = {
        DISBURSEMENT:  { icon: '📤', label: 'Disbursement',   color: 'credit',  sign: '+' },
        REPAYMENT:     { icon: '💵', label: 'Payment',        color: 'credit',  sign: '-' },
        PENALTY:       { icon: '⚠️', label: 'Penalty',        color: 'debit',   sign: '+' },
        ROLLOVER_FEE:  { icon: '🔄', label: 'Rollover Fee',   color: 'debit',   sign: '+' },
        SETTLEMENT:    { icon: '✅', label: 'Settlement',     color: 'credit',  sign: '-' },
        WRITE_OFF:     { icon: '📋', label: 'Write-off',      color: 'pending', sign: ''  },
        RECOVERY:      { icon: '💰', label: 'Recovery',       color: 'credit',  sign: '-' },
    };
    const isPendingInfo = loan.status === 'PENDING_INFO';
    const isRejected = loan.status === 'REJECTED';

    return (
        <div style={{ paddingBottom: 100 }}>
            {/* Header */}
            <div className="page-header">
                <div className="page-header-back" onClick={() => navigate({ name: 'loans' })}>
                    <ArrowLeft size={20} />
                </div>
                <span className="page-header-title">{loan.loan_number}</span>
                <span className={`badge badge-${loan.status === 'ACTIVE' ? 'active' : loan.status === 'OVERDUE' ? 'overdue' : loan.status === 'PENDING_INFO' ? 'info' : 'pending'}`}>
                    {loan.status === 'PENDING_INFO' ? 'Info Required' : loan.status?.replace(/_/g, ' ')}
                </span>
            </div>

            {/* Balance Card */}
            <div style={{ padding: '0 20px', marginTop: 16 }}>
                <div style={{
                    background: 'linear-gradient(145deg, var(--primary-950), var(--primary-800))',
                    borderRadius: 'var(--radius)',
                    padding: 24,
                    color: 'white',
                    position: 'relative',
                    overflow: 'hidden',
                }}>
                    <div style={{
                        position: 'absolute',
                        top: -20,
                        right: -20,
                        width: 120,
                        height: 120,
                        background: 'radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 60%)',
                        borderRadius: '50%',
                    }}></div>
                    <div style={{ fontSize: 12, opacity: 0.7, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        Outstanding Balance
                    </div>
                    <div style={{ fontSize: 36, fontWeight: 800, marginTop: 4, letterSpacing: '-0.02em' }}>
                        ZMW {outstanding.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </div>
                    {isActive && (
                        <div style={{ marginTop: 16 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, opacity: 0.7, marginBottom: 6 }}>
                                <span>{progress.toFixed(0)}% Repaid</span>
                                <span>ZMW {parseFloat(loan.total_repayable || 0).toLocaleString()} total</span>
                            </div>
                            <div style={{ height: 6, background: 'rgba(255,255,255,0.2)', borderRadius: 100, overflow: 'hidden' }}>
                                <div style={{
                                    height: '100%',
                                    width: `${progress}%`,
                                    background: 'rgba(255,255,255,0.9)',
                                    borderRadius: 100,
                                    transition: 'width 0.6s ease',
                                }}></div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Rejection Banner */}
            {isRejected && (
                <div style={{ padding: '16px 20px' }}>
                    <div style={{
                        background: '#FEF2F2',
                        border: '1.5px solid #FECACA',
                        borderRadius: 12,
                        padding: 16,
                    }}>
                        <div style={{ fontWeight: 700, color: '#991B1B', marginBottom: 6, fontSize: 15 }}>
                            ✕ Loan Application Rejected
                        </div>
                        {loan.rejection_reason ? (
                            <div style={{
                                background: 'white',
                                border: '1px solid #FECACA',
                                borderRadius: 8,
                                padding: 12,
                                fontSize: 13,
                                color: '#7F1D1D',
                                lineHeight: 1.6,
                            }}>
                                {loan.rejection_reason}
                            </div>
                        ) : (
                            <p style={{ fontSize: 13, color: '#991B1B', margin: 0 }}>
                                No reason provided. Please contact our office for more details.
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Pending Info Banner */}
            {isPendingInfo && (
                <div style={{ padding: '16px 20px' }}>
                    <div style={{
                        background: '#EFF6FF',
                        border: '1.5px solid #BFDBFE',
                        borderRadius: 12,
                        padding: 16,
                    }}>
                        <div style={{ fontWeight: 700, color: '#1E40AF', marginBottom: 8, fontSize: 15 }}>
                            ℹ Information Required
                        </div>
                        <p style={{ fontSize: 13, color: '#1E3A8A', marginBottom: 12, lineHeight: 1.6 }}>
                            Our underwriting team has reviewed your application and needs the following information before proceeding:
                        </p>
                        <div style={{
                            background: 'white',
                            border: '1px solid #BFDBFE',
                            borderRadius: 8,
                            padding: 12,
                            fontSize: 13,
                            color: '#1E3A8A',
                            marginBottom: 14,
                            lineHeight: 1.6,
                        }}>
                            {loan.info_request_note}
                        </div>
                        {infoSubmitted ? (
                            <div style={{ fontSize: 13, color: '#15803D', fontWeight: 600 }}>
                                ✅ Your response has been submitted. We will review it shortly.
                            </div>
                        ) : (
                            <>
                                <textarea
                                    style={{
                                        width: '100%',
                                        border: '1.5px solid #BFDBFE',
                                        borderRadius: 8,
                                        padding: '10px 12px',
                                        fontSize: 13,
                                        fontFamily: 'inherit',
                                        resize: 'vertical',
                                        marginBottom: 10,
                                        outline: 'none',
                                        boxSizing: 'border-box',
                                    }}
                                    rows={4}
                                    placeholder="Type your response here... (optional if uploading documents)"
                                    value={infoResponse}
                                    onChange={e => setInfoResponse(e.target.value)}
                                />
                                {/* File upload */}
                                <label style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 8,
                                    border: '1.5px dashed #BFDBFE',
                                    borderRadius: 8,
                                    padding: '10px 12px',
                                    fontSize: 13,
                                    color: '#1E40AF',
                                    cursor: 'pointer',
                                    marginBottom: 8,
                                    background: 'white',
                                }}>
                                    <input
                                        type="file"
                                        multiple
                                        style={{ display: 'none' }}
                                        onChange={e => setInfoFiles(Array.from(e.target.files || []))}
                                    />
                                    📎 {infoFiles.length > 0 ? `${infoFiles.length} file(s) selected` : 'Attach documents (optional)'}
                                </label>
                                {infoFiles.length > 0 && (
                                    <div style={{ marginBottom: 10 }}>
                                        {infoFiles.map((f, i) => (
                                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: '#1E3A8A', padding: '3px 4px' }}>
                                                <span>📄 {f.name}</span>
                                                <button
                                                    onClick={() => setInfoFiles(prev => prev.filter((_, j) => j !== i))}
                                                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#991B1B', fontSize: 14, padding: '0 4px' }}
                                                >✕</button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <button
                                    className="btn btn-primary"
                                    onClick={handleProvideInfo}
                                    disabled={(!infoResponse.trim() && infoFiles.length === 0) || infoSubmitting}
                                    style={{ width: '100%', justifyContent: 'center' }}
                                >
                                    {infoSubmitting ? <span className="loading-spinner" style={{ width: 16, height: 16 }}></span> : <Send size={15} />}
                                    Submit Response
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Action Buttons */}
            {isActive && (
                <div style={{ padding: '16px 20px', display: 'flex', gap: 10 }}>
                    <button
                        className="btn btn-primary"
                        onClick={() => navigate({ name: 'payment', loanId: loan.id })}
                    >
                        <Send size={16} />
                        Make Payment
                    </button>
                </div>
            )}

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 0, borderBottom: '2px solid var(--gray-100)', margin: '0 20px' }}>
                {(['details', 'transactions'] as const).map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        style={{
                            padding: '10px 20px',
                            fontSize: 14,
                            fontWeight: 600,
                            border: 'none',
                            background: 'none',
                            cursor: 'pointer',
                            color: activeTab === tab ? 'var(--primary-600)' : 'var(--gray-400)',
                            borderBottom: `2px solid ${activeTab === tab ? 'var(--primary-600)' : 'transparent'}`,
                            marginBottom: -2,
                            fontFamily: 'inherit',
                            textTransform: 'capitalize',
                        }}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="section animate-in" key={activeTab}>
                {activeTab === 'details' ? (
                    <div className="card">
                        <div className="card-body" style={{ padding: 0 }}>
                            <div style={{ padding: '16px 20px' }}>
                                {[
                                    ['Product', loan.product_name || 'N/A'],
                                    ['Principal Amount', `ZMW ${parseFloat(loan.amount || 0).toLocaleString()}`],
                                    ['Total Repayable', `ZMW ${parseFloat(loan.total_repayable || 0).toLocaleString()}`],
                                    [FREQ_LABEL[loan.repayment_frequency] || 'Installment', `ZMW ${parseFloat(loan.monthly_payment || 0).toLocaleString()}`],
                                    ['Repayment Frequency', FREQ_DISPLAY[loan.repayment_frequency] || 'Monthly'],
                                    ['Interest Rate', `${loan.interest_rate}%`],
                                    ['Term', `${loan.term_months} months`],
                                    ['Amount Repaid', `ZMW ${parseFloat(loan.repaid_amount || 0).toLocaleString()}`],
                                    ['Disbursement Date', loan.disbursement_date || 'N/A'],
                                    ['Maturity Date', loan.maturity_date || 'N/A'],
                                    ['Days Overdue', loan.days_overdue || 0],
                                    ['Rollovers Used', `${loan.rollover_count || 0}`],
                                    ['Purpose', loan.purpose || 'N/A'],
                                ].map(([label, value]) => (
                                    <div className="info-row" key={label}>
                                        <span className="info-label">{label}</span>
                                        <span className="info-value">{value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div>
                        {ledger.length === 0 ? (
                            <div className="empty-state" style={{ padding: '40px 20px' }}>
                                <div className="empty-state-icon">📝</div>
                                <h3>No Transactions</h3>
                                <p>Transaction history will appear here.</p>
                            </div>
                        ) : (
                            <div className="card">
                                <div className="card-body" style={{ padding: 0 }}>
                                    {ledger.map((tx: any, i: number) => {
                                        const meta = TX_META[tx.transaction_type] ?? { icon: '📋', label: tx.transaction_type?.replace(/_/g, ' '), color: 'pending', sign: '' };
                                        const amt = parseFloat(tx.amount || 0);
                                        return (
                                            <div key={tx.id || i} style={{
                                                padding: '14px 16px',
                                                borderBottom: i < ledger.length - 1 ? '1px solid var(--gray-100)' : 'none',
                                            }}>
                                                {/* Main row */}
                                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                                                    <div className={`tx-icon ${meta.color}`} style={{ flexShrink: 0 }}>
                                                        {meta.icon}
                                                    </div>
                                                    <div style={{ flex: 1, minWidth: 0 }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                            <div>
                                                                <div className="tx-title">{meta.label}</div>
                                                                <div className="tx-date">
                                                                    {new Date(tx.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                                                                    {tx.reference ? ` · ${tx.reference}` : ''}
                                                                </div>
                                                            </div>
                                                            <div style={{ textAlign: 'right' }}>
                                                                <div className={`tx-amount ${meta.color}`}>
                                                                    {meta.sign}ZMW {amt.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                                                </div>
                                                                <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 2 }}>
                                                                    Bal: ZMW {tx._balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* Disbursement breakdown */}
                                                        {tx.transaction_type === 'DISBURSEMENT' && (
                                                            <div style={{
                                                                marginTop: 8,
                                                                padding: '8px 10px',
                                                                background: 'var(--gray-50)',
                                                                borderRadius: 8,
                                                                display: 'flex',
                                                                gap: 16,
                                                                fontSize: 12,
                                                            }}>
                                                                <div>
                                                                    <div style={{ color: 'var(--gray-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Principal</div>
                                                                    <div style={{ color: 'var(--gray-800)', fontWeight: 700 }}>ZMW {amt.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                                                                </div>
                                                                <div>
                                                                    <div style={{ color: 'var(--gray-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Interest & Fees</div>
                                                                    <div style={{ color: 'var(--error)', fontWeight: 700 }}>ZMW {totalInterest.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                                                                </div>
                                                                <div>
                                                                    <div style={{ color: 'var(--gray-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Repayable</div>
                                                                    <div style={{ color: 'var(--gray-800)', fontWeight: 700 }}>ZMW {totalRepayable.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Notes */}
                                                        {tx.notes && (
                                                            <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 4 }}>{tx.notes}</div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
