import { useState, useEffect } from 'react';
import { productsAPI, loansAPI, clientsAPI, kycAPI } from '../services/api';
import { ArrowLeft, ChevronRight, Check, CreditCard, AlertCircle } from 'lucide-react';
import type { Page } from '../components/AppShell';

interface ApplyPageProps {
    navigate: (page: Page) => void;
}

interface LoanSummary {
    total_interest: number;
    total_repayable: number;
    monthly_payment: number;
}

const EMPTY_SUMMARY: LoanSummary = {
    total_interest: 0,
    total_repayable: 0,
    monthly_payment: 0,
};

function formatCurrency(value: number): string {
    return value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

export default function ApplyPage({ navigate }: ApplyPageProps) {
    const [step, setStep] = useState(1);
    const [products, setProducts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [kycStatus, setKycStatus] = useState<string | null>(null);
    const [kycVerified, setKycVerified] = useState(false);
    const [kycRequired, setKycRequired] = useState(true);
    const [loanSummary, setLoanSummary] = useState<LoanSummary>(EMPTY_SUMMARY);
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [summaryError, setSummaryError] = useState('');

    // Form state
    const [selectedProduct, setSelectedProduct] = useState<any>(null);
    const [amount, setAmount] = useState(5000);
    const [term, setTerm] = useState(3);
    const [purpose, setPurpose] = useState('');

    const getProductMinAmount = (product: any) => Number(product.min_amount ?? 0);
    const getProductMaxAmount = (product: any) => Number(product.client_max_borrow_amount ?? product.max_amount ?? 0);
    const canApplyForProduct = (product: any) => getProductMaxAmount(product) >= getProductMinAmount(product);
    const hasAnyEligibleProduct = products.some(product => product.is_active && canApplyForProduct(product));

    useEffect(() => {
        Promise.all([
            productsAPI.list(),
            clientsAPI.list(),
            kycAPI.sections(),
        ])
            .then(([productsRes, clientsRes, sectionsRes]) => {
                const data = productsRes.data?.results || productsRes.data || [];
                setProducts(Array.isArray(data) ? data : []);

                const profile = Array.isArray(clientsRes.data) ? clientsRes.data[0] : clientsRes.data?.results?.[0];
                if (profile) {
                    setKycVerified(profile.kyc_verified);
                    setKycStatus(profile.vetting_status);
                }

                const sections = Array.isArray(sectionsRes.data?.results)
                    ? sectionsRes.data.results
                    : (Array.isArray(sectionsRes.data) ? sectionsRes.data : []);
                const activeSections = sections.filter(
                    (section: any) => section.is_active && Array.isArray(section.fields) && section.fields.length > 0
                );
                setKycRequired(activeSections.length > 0);
            })
            .catch(() => setProducts([]))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (!selectedProduct || amount <= 0 || term <= 0) {
            setLoanSummary(EMPTY_SUMMARY);
            setSummaryLoading(false);
            setSummaryError('');
            return;
        }

        let cancelled = false;
        const timeoutId = window.setTimeout(async () => {
            setSummaryLoading(true);
            setSummaryError('');
            try {
                const res = await loansAPI.calculate({
                    product: selectedProduct.id,
                    principal: amount,
                    term_months: term,
                });
                if (cancelled) return;

                setLoanSummary({
                    total_interest: Number(res.data?.total_interest ?? 0),
                    total_repayable: Number(res.data?.total_repayable ?? 0),
                    monthly_payment: Number(res.data?.monthly_payment ?? 0),
                });
            } catch {
                if (cancelled) return;
                setLoanSummary(EMPTY_SUMMARY);
                setSummaryError('Unable to calculate the loan summary right now.');
            } finally {
                if (!cancelled) {
                    setSummaryLoading(false);
                }
            }
        }, 150);

        return () => {
            cancelled = true;
            window.clearTimeout(timeoutId);
        };
    }, [selectedProduct?.id, amount, term]);

    const handleSubmit = async () => {
        if (!selectedProduct) return;
        setSubmitting(true);
        setError('');
        try {
            await loansAPI.create({
                product: selectedProduct.id,
                amount,
                term_months: term,
                purpose,
            });
            setSuccess(true);
        } catch (err: any) {
            const data = err.response?.data;
            let errorMsg = 'Failed to submit application. Please try again.';
            if (data) {
                if (data.detail) errorMsg = data.detail;
                else if (data.error) errorMsg = data.error;
                else if (data.non_field_errors && data.non_field_errors.length) errorMsg = data.non_field_errors[0];
                else if (typeof data === 'object') {
                    const firstKey = Object.keys(data)[0];
                    if (firstKey && Array.isArray(data[firstKey])) {
                        errorMsg = data[firstKey][0];
                    }
                }
            }
            setError(errorMsg);
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
                }}>
                    <Check size={36} color="var(--success)" />
                </div>
                <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--gray-900)', marginBottom: 8 }}>Application Submitted!</h2>
                <p style={{ fontSize: 14, color: 'var(--gray-500)', lineHeight: 1.6, marginBottom: 32, maxWidth: 300 }}>
                    Your loan application has been submitted for review. We'll notify you once it's approved.
                </p>
                <button className="btn btn-primary" style={{ width: 'auto' }} onClick={() => navigate({ name: 'loans' })}>
                    View My Loans
                </button>
            </div>
        );
    }

    if (!loading && kycRequired && !kycVerified) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '80vh', padding: 40, textAlign: 'center' }}>
                <div style={{
                    width: 80, height: 80, borderRadius: '50%', background: 'var(--warning-light)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 24,
                }}>
                    <AlertCircle size={36} color="var(--warning)" />
                </div>
                <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--gray-900)', marginBottom: 8 }}>Action Required</h2>
                <p style={{ fontSize: 14, color: 'var(--gray-500)', lineHeight: 1.6, marginBottom: 24, maxWidth: 320 }}>
                    You cannot borrow at this time. Please provide additional information to our office to qualify.
                </p>
                {kycStatus === 'PENDING' ? (
                    <div className="alert alert-info">Your KYC application is currently under review.</div>
                ) : (
                    <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => navigate({ name: 'kyc' })}>
                        Complete KYC Profile
                    </button>
                )}
            </div>
        );
    }

    return (
        <div style={{ paddingBottom: 100 }}>
            {/* Header */}
            <div className="page-header">
                <div className="page-header-back" onClick={() => {
                    if (step > 1) setStep(step - 1);
                    else navigate({ name: 'dashboard' });
                }}>
                    <ArrowLeft size={20} />
                </div>
                <span className="page-header-title">Apply for Loan</span>
            </div>

            {/* Steps */}
            <div className="steps" style={{ margin: '16px 0' }}>
                {['Product', 'Amount', 'Review'].map((label, i) => (
                    <div key={label} className={`step ${step > i + 1 ? 'completed' : ''} ${step === i + 1 ? 'active' : ''}`}>
                        <div className="step-dot">
                            {step > i + 1 ? <Check size={14} /> : i + 1}
                        </div>
                        <div className="step-label">{label}</div>
                    </div>
                ))}
            </div>

            {/* Step 1: Select Product */}
            {step === 1 && (
                <div className="section animate-in">
                    <h2 className="section-title" style={{ marginBottom: 16 }}>Choose a Loan Product</h2>

                    {loading ? (
                        Array.from({ length: 3 }).map((_, i) => (
                            <div key={i} className="skeleton" style={{ width: '100%', height: 140, marginBottom: 12, borderRadius: 16 }}></div>
                        ))
                    ) : products.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">📦</div>
                            <h3>No Products Available</h3>
                            <p>No loan products are available at this time.</p>
                        </div>
                    ) : (
                        products.filter(p => p.is_active).map(product => (
                            <div
                                key={product.id}
                                className="product-card"
                                onClick={() => {
                                    if (!canApplyForProduct(product)) return;
                                    setSelectedProduct(product);
                                    const minAmount = getProductMinAmount(product);
                                    const maxAmount = getProductMaxAmount(product);
                                    setAmount(Math.min(maxAmount, Math.max(minAmount, amount)));
                                    setTerm(Math.max(product.min_term, Math.min(term, product.max_term)));
                                    setStep(2);
                                }}
                                style={{
                                    cursor: canApplyForProduct(product) ? 'pointer' : 'not-allowed',
                                    opacity: canApplyForProduct(product) ? 1 : 0.65,
                                    border: selectedProduct?.id === product.id ? '2px solid var(--primary-500)' : '1px solid var(--gray-100)',
                                }}
                            >
                                <div className="product-card-header">
                                    <div className="product-card-icon">💰</div>
                                    <div style={{ flex: 1 }}>
                                        <div className="product-card-name">{product.name}</div>
                                        <div className="product-card-rate">{product.interest_rate}% interest</div>
                                    </div>
                                    <ChevronRight size={20} color="var(--gray-400)" />
                                </div>
                                <div className="product-card-details">
                                    <div className="product-detail">
                                        <div className="product-detail-label">Min Amount</div>
                                        <div className="product-detail-value">ZMW {parseFloat(product.min_amount).toLocaleString()}</div>
                                    </div>
                                    <div className="product-detail">
                                        <div className="product-detail-label">Max Amount</div>
                                        <div className="product-detail-value">ZMW {getProductMaxAmount(product).toLocaleString()}</div>
                                    </div>
                                    <div className="product-detail">
                                        <div className="product-detail-label">Term</div>
                                        <div className="product-detail-value">{product.min_term}-{product.max_term} months</div>
                                    </div>
                                    <div className="product-detail">
                                        <div className="product-detail-label">Type</div>
                                        <div className="product-detail-value">{product.interest_type?.replace('_', ' ')}</div>
                                    </div>
                                </div>
                                {!canApplyForProduct(product) && (
                                    <div className="alert alert-error" style={{ marginTop: 12 }}>
                                        <AlertCircle size={16} />
                                        <span>Sorry, you do not qualify for this product at this time.</span>
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                    {!loading && !hasAnyEligibleProduct && products.some(product => product.is_active) && (
                        <div className="alert alert-error" style={{ marginTop: 16 }}>
                            <AlertCircle size={16} />
                            <span>Sorry, you do not qualify for a loan at this time. If you believe this is an error, contact the our sales team.</span>
                        </div>
                    )}
                </div>
            )}

            {/* Step 2: Amount & Details */}
            {step === 2 && selectedProduct && canApplyForProduct(selectedProduct) && (
                <div className="section animate-in">
                    <div className="amount-display">
                        <div className="amount-currency">ZMW</div>
                        <div className="amount-value">{amount.toLocaleString()}</div>
                    </div>

                    <div style={{ padding: '0 4px', marginBottom: 24 }}>
                        <input
                            type="range"
                            className="amount-slider"
                            min={getProductMinAmount(selectedProduct)}
                            max={getProductMaxAmount(selectedProduct)}
                            step={500}
                            value={amount}
                            onChange={e => setAmount(Number(e.target.value))}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--gray-400)' }}>
                            <span>ZMW {getProductMinAmount(selectedProduct).toLocaleString()}</span>
                            <span>ZMW {getProductMaxAmount(selectedProduct).toLocaleString()}</span>
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Repayment Period</label>
                        <select
                            className="form-control"
                            value={term}
                            onChange={e => setTerm(Number(e.target.value))}
                        >
                            {Array.from(
                                { length: selectedProduct.max_term - selectedProduct.min_term + 1 },
                                (_, i) => selectedProduct.min_term + i
                            ).map((m: number) => (
                                <option key={m} value={m}>{m} month{m > 1 ? 's' : ''}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Purpose</label>
                        <textarea
                            className="form-control"
                            placeholder="What is this loan for?"
                            value={purpose}
                            onChange={e => setPurpose(e.target.value)}
                            rows={3}
                        />
                    </div>

                    {/* Summary */}
                    <div className="card" style={{ marginTop: 16 }}>
                        <div className="card-body" style={{ padding: '16px 20px' }}>
                            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 12 }}>Loan Summary</div>
                            {summaryError ? (
                                <div className="alert alert-error">
                                    <AlertCircle size={16} />
                                    <span>{summaryError}</span>
                                </div>
                            ) : summaryLoading ? (
                                <div style={{ display: 'flex', justifyContent: 'center', padding: '16px 0' }}>
                                    <div className="loading-spinner" style={{ width: 24, height: 24, borderWidth: 2 }}></div>
                                </div>
                            ) : (
                                [
                                    ['Principal', `ZMW ${amount.toLocaleString()}`],
                                    ['Total Rate', `${Number(selectedProduct.interest_rate ?? 0).toFixed(2)}%`],
                                    ['Term', `${term} months`],
                                    ['Est. Charges', `ZMW ${formatCurrency(loanSummary.total_interest)}`],
                                    ['Total Repayable', `ZMW ${formatCurrency(loanSummary.total_repayable)}`],
                                    ['Monthly Payment', `ZMW ${formatCurrency(loanSummary.monthly_payment)}`],
                                ].map(([label, value]) => (
                                    <div className="info-row" key={label} style={{ padding: '8px 0' }}>
                                        <span className="info-label">{label}</span>
                                        <span className="info-value">{value}</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                        <button className="btn btn-secondary" onClick={() => setStep(1)}>Back</button>
                        <button
                            className="btn btn-primary"
                            disabled={!purpose.trim() || summaryLoading || !!summaryError}
                            onClick={() => setStep(3)}
                        >
                            Continue
                        </button>
                    </div>
                </div>
            )}

            {/* Step 3: Review & Submit */}
            {step === 3 && selectedProduct && (
                <div className="section animate-in">
                    <div className="card" style={{ marginBottom: 16 }}>
                        <div className="card-body">
                            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 16 }}>Review Your Application</div>
                            {summaryError ? (
                                <div className="alert alert-error">
                                    <AlertCircle size={16} />
                                    <span>{summaryError}</span>
                                </div>
                            ) : summaryLoading ? (
                                <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0' }}>
                                    <div className="loading-spinner" style={{ width: 24, height: 24, borderWidth: 2 }}></div>
                                </div>
                            ) : (
                                [
                                    ['Product', selectedProduct.name],
                                    ['Amount', `ZMW ${amount.toLocaleString()}`],
                                    ['Term', `${term} months`],
                                    ['Total Rate', `${Number(selectedProduct.interest_rate ?? 0).toFixed(2)}%`],
                                    ['Estimated Charges', `ZMW ${formatCurrency(loanSummary.total_interest)}`],
                                    ['Total Repayable', `ZMW ${formatCurrency(loanSummary.total_repayable)}`],
                                    ['Monthly Payment', `ZMW ${formatCurrency(loanSummary.monthly_payment)}`],
                                    ['Purpose', purpose],
                                ].map(([label, value]) => (
                                    <div className="info-row" key={label}>
                                        <span className="info-label">{label}</span>
                                        <span className="info-value" style={{ maxWidth: '60%', wordBreak: 'break-word' }}>{value}</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="alert alert-info">
                        <AlertCircle size={16} />
                        <span>Your application will be reviewed by our team. Approval typically takes 1-2 business days.</span>
                    </div>

                    {error && (
                        <div className="alert alert-error">
                            <AlertCircle size={16} />
                            <span>{error}</span>
                        </div>
                    )}

                    <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                        <button className="btn btn-secondary" onClick={() => setStep(2)}>Back</button>
                        <button
                            className="btn btn-primary"
                            onClick={handleSubmit}
                            disabled={submitting || summaryLoading || !!summaryError}
                        >
                            {submitting ? (
                                <div className="loading-spinner" style={{ width: 18, height: 18, borderWidth: 2 }}></div>
                            ) : (
                                <>
                                    <CreditCard size={16} />
                                    Submit Application
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
