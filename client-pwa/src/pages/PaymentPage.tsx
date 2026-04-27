import { useState, useEffect } from 'react';
import { loansAPI } from '../services/api';
import { ArrowLeft, Check, AlertCircle, Send, Pencil } from 'lucide-react';
import type { Page } from '../components/AppShell';

interface PaymentPageProps {
    loanId: number;
    navigate: (page: Page) => void;
}

const QUICK_AMOUNTS = [100, 500, 1000, 2500];

export default function PaymentPage({ loanId, navigate }: PaymentPageProps) {
    const [loan, setLoan] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [amount, setAmount] = useState('');
    const [notes, setNotes] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        loansAPI.get(loanId)
            .then(res => {
                setLoan(res.data);
                const nextDue = parseFloat(res.data?.next_payment_due ?? res.data?.monthly_payment ?? 0);
                if (nextDue > 0) setAmount(nextDue.toString());
            })
            .catch(() => { })
            .finally(() => setLoading(false));
    }, [loanId]);

    const handleSubmit = async () => {
        const numAmount = parseFloat(amount);
        if (!numAmount || numAmount <= 0) return;
        setSubmitting(true);
        setError('');
        try {
            await loansAPI.repay(loanId, numAmount, notes || undefined);
            setSuccess(true);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.response?.data?.error || 'Payment failed. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    if (success) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '80vh', padding: 40, textAlign: 'center' }}>
                <div style={{
                    width: 80,
                    height: 80,
                    borderRadius: '50%',
                    background: 'var(--success-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 24,
                    animation: 'scaleIn 0.4s ease',
                }}>
                    <Check size={36} color="var(--success)" />
                </div>
                <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--gray-900)', marginBottom: 8 }}>Payment Successful!</h2>
                <p style={{ fontSize: 14, color: 'var(--gray-500)', lineHeight: 1.6, marginBottom: 32 }}>
                    Your payment of <strong>ZMW {parseFloat(amount).toLocaleString()}</strong> has been processed.
                </p>
                <div style={{ display: 'flex', gap: 10, width: '100%', maxWidth: 300 }}>
                    <button className="btn btn-secondary" onClick={() => navigate({ name: 'loan-detail', loanId })}>
                        View Loan
                    </button>
                    <button className="btn btn-primary" onClick={() => navigate({ name: 'dashboard' })}>
                        Home
                    </button>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div>
                <div className="page-header">
                    <div className="page-header-back" onClick={() => navigate({ name: 'loan-detail', loanId })}>
                        <ArrowLeft size={20} />
                    </div>
                    <span className="page-header-title">Make Payment</span>
                </div>
                <div className="page-loader">
                    <div className="loading-spinner" style={{ width: 32, height: 32 }}></div>
                </div>
            </div>
        );
    }

    const outstanding = parseFloat(loan?.outstanding_balance || 0);
    const canPay = loan?.status === 'ACTIVE' || loan?.status === 'OVERDUE';

    if (!canPay) {
        return (
            <div>
                <div className="page-header">
                    <div className="page-header-back" onClick={() => navigate({ name: 'loan-detail', loanId })}>
                        <ArrowLeft size={20} />
                    </div>
                    <span className="page-header-title">Make Payment</span>
                </div>
                <div className="empty-state">
                    <AlertCircle size={34} color="var(--warning)" />
                    <h3>Payment Not Available</h3>
                    <p>This loan has not been disbursed yet. Payments can only be made once a loan is active.</p>
                    <button className="btn btn-secondary" style={{ margin: '0 auto', width: 'auto' }} onClick={() => navigate({ name: 'loan-detail', loanId })}>
                        Back to Loan
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ paddingBottom: 40 }}>
            {/* Header */}
            <div className="page-header">
                <div className="page-header-back" onClick={() => navigate({ name: 'loan-detail', loanId })}>
                    <ArrowLeft size={20} />
                </div>
                <span className="page-header-title">Make Payment</span>
            </div>

            {/* Loan Info */}
            <div style={{ padding: '16px 20px' }}>
                <div className="card">
                    <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div style={{ fontSize: 13, color: 'var(--gray-500)', fontWeight: 500 }}>{loan?.loan_number}</div>
                            <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 2 }}>{loan?.product_name || 'Loan'}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: 11, color: 'var(--gray-400)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>Outstanding</div>
                            <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--gray-900)' }}>ZMW {outstanding.toLocaleString()}</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Amount Input */}
            <div style={{ padding: '0 20px' }}>
                <div className="amount-display">
                    <div style={{ fontSize: 12, color: 'var(--gray-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                        <Pencil size={11} />
                        Enter Amount
                    </div>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                        borderBottom: '2.5px solid var(--primary-400)',
                        paddingBottom: 8,
                        marginBottom: 4,
                    }}>
                        <div className="amount-currency">ZMW</div>
                        <input
                            type="number"
                            value={amount}
                            onChange={e => setAmount(e.target.value)}
                            placeholder="0.00"
                            style={{
                                fontSize: 48,
                                fontWeight: 800,
                                color: 'var(--gray-900)',
                                border: 'none',
                                outline: 'none',
                                textAlign: 'center',
                                width: '100%',
                                background: 'transparent',
                                fontFamily: 'inherit',
                                letterSpacing: '-0.03em',
                            }}
                        />
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--primary-500)', textAlign: 'center', marginBottom: 4 }}>
                        Tap amount above to edit
                    </div>
                </div>

                {/* Quick Amounts */}
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 24, flexWrap: 'wrap' }}>
                    {QUICK_AMOUNTS.map(qa => (
                        <button
                            key={qa}
                            onClick={() => setAmount(qa.toString())}
                            style={{
                                padding: '8px 18px',
                                borderRadius: 'var(--radius-full)',
                                fontSize: 14,
                                fontWeight: 600,
                                border: 'none',
                                cursor: 'pointer',
                                background: parseFloat(amount) === qa ? 'var(--primary-600)' : 'var(--gray-100)',
                                color: parseFloat(amount) === qa ? 'white' : 'var(--gray-600)',
                                transition: 'all 0.2s',
                                fontFamily: 'inherit',
                            }}
                        >
                            ZMW {qa.toLocaleString()}
                        </button>
                    ))}
                    <button
                        onClick={() => setAmount(outstanding.toString())}
                        style={{
                            padding: '8px 18px',
                            borderRadius: 'var(--radius-full)',
                            fontSize: 14,
                            fontWeight: 600,
                            border: '1.5px solid var(--primary-300)',
                            cursor: 'pointer',
                            background: parseFloat(amount) === outstanding ? 'var(--primary-600)' : 'transparent',
                            color: parseFloat(amount) === outstanding ? 'white' : 'var(--primary-600)',
                            transition: 'all 0.2s',
                            fontFamily: 'inherit',
                        }}
                    >
                        Pay All
                    </button>
                </div>

                {/* Notes */}
                <div className="form-group">
                    <label className="form-label">Payment Notes (optional)</label>
                    <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Monthly payment"
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                    />
                </div>

                {error && (
                    <div className="alert alert-error">
                        <AlertCircle size={16} />
                        <span>{error}</span>
                    </div>
                )}

                {/* Submit */}
                <button
                    className="btn btn-primary btn-lg"
                    onClick={handleSubmit}
                    disabled={submitting || !parseFloat(amount) || parseFloat(amount) <= 0}
                    style={{ marginTop: 16 }}
                >
                    {submitting ? (
                        <div className="loading-spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                    ) : (
                        <>
                            <Send size={18} />
                            Pay ZMW {parseFloat(amount || '0').toLocaleString()}
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
