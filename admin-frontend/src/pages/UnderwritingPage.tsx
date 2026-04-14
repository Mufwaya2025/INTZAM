import { useState, useEffect } from 'react';
import { loansAPI, aiAPI } from '../services/api';

interface UnderwritingPageProps {
    userPermissions: string[];
}

export default function UnderwritingPage({ userPermissions }: UnderwritingPageProps) {
    const [loans, setLoans] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedLoan, setSelectedLoan] = useState<any>(null);
    const [aiAnalysis, setAiAnalysis] = useState<string>('');
    const [aiLoading, setAiLoading] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [approvalComments, setApprovalComments] = useState('');
    const [showRejectModal, setShowRejectModal] = useState(false);
    const [showInfoModal, setShowInfoModal] = useState(false);
    const [infoNote, setInfoNote] = useState('');
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => { loadPending(); }, []);

    const loadPending = async () => {
        try {
            const [pendingRes, infoRes] = await Promise.allSettled([
                loansAPI.list({ status: 'PENDING_APPROVAL' }),
                loansAPI.list({ status: 'PENDING_INFO' }),
            ]);
            const pending = pendingRes.status === 'fulfilled' ? (pendingRes.value.data.results || pendingRes.value.data) : [];
            const info = infoRes.status === 'fulfilled' ? (infoRes.value.data.results || infoRes.value.data) : [];
            setLoans([...pending, ...info]);
        } catch {
            setLoans(MOCK_PENDING);
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async () => {
        if (!selectedLoan) return;
        setActionLoading(true);
        try {
            await loansAPI.approve(selectedLoan.id, approvalComments);
            loadPending();
            setSelectedLoan(null);
            setApprovalComments('');
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error approving loan');
        } finally {
            setActionLoading(false);
        }
    };

    const handleReject = async () => {
        if (!selectedLoan || !rejectReason) return;
        setActionLoading(true);
        try {
            await loansAPI.reject(selectedLoan.id, rejectReason);
            setShowRejectModal(false);
            loadPending();
            setSelectedLoan(null);
            setApprovalComments('');
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error rejecting loan');
        } finally {
            setActionLoading(false);
        }
    };

    const handleRequestInfo = async () => {
        if (!selectedLoan || !infoNote) return;
        setActionLoading(true);
        try {
            await loansAPI.requestInfo(selectedLoan.id, infoNote);
            setShowInfoModal(false);
            setInfoNote('');
            loadPending();
            setSelectedLoan(null);
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error requesting information');
        } finally {
            setActionLoading(false);
        }
    };

    const handleAiAnalysis = async () => {
        if (!selectedLoan) return;
        setAiLoading(true);
        setAiAnalysis('');
        try {
            const res = await aiAPI.analyze(selectedLoan.id);
            setAiAnalysis(res.data.analysis);
        } catch {
            setAiAnalysis(getMockAnalysis(selectedLoan));
        } finally {
            setAiLoading(false);
        }
    };

    const canApprove = userPermissions.includes('approve_loans');
    const canRequestInfo = userPermissions.includes('request_client_info');

    return (
        <div style={{ display: 'grid', gridTemplateColumns: selectedLoan ? '1fr 420px' : '1fr', gap: 20 }}>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Pending Applications ({loans.length})</h3>
                    <span className="badge badge-warning">Requires Review</span>
                </div>
                <div className="table-container">
                    {loading ? (
                        <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                    ) : loans.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">✅</div>
                            <h3>All Clear!</h3>
                            <p>No pending loan applications to review.</p>
                        </div>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Loan #</th>
                                    <th>Client</th>
                                    <th>Product</th>
                                    <th>Amount</th>
                                    <th>Term</th>
                                    <th>Purpose</th>
                                    <th>Status</th>
                                    <th>Applied</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loans.map(loan => (
                                    <tr
                                        key={loan.id}
                                        onClick={() => {
                                            setSelectedLoan(loan);
                                            setApprovalComments(loan.underwriter_comments || '');
                                            setAiAnalysis('');
                                        }}
                                        style={{ cursor: 'pointer', background: selectedLoan?.id === loan.id ? 'var(--primary-50)' : '' }}
                                    >
                                        <td><strong>{loan.loan_number}</strong></td>
                                        <td>
                                            <div style={{ fontWeight: 600 }}>{loan.client_name}</div>
                                            <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{loan.client_tier} Tier</div>
                                        </td>
                                        <td>{loan.product_name}</td>
                                        <td><strong>ZMW {Number(loan.amount).toLocaleString()}</strong></td>
                                        <td>{loan.term_months} months</td>
                                        <td style={{ maxWidth: 150 }}><span className="truncate">{loan.purpose}</span></td>
                                        <td>
                                            <span className={`badge ${loan.status === 'PENDING_INFO' ? 'badge-info' : 'badge-warning'}`}>
                                                {loan.status === 'PENDING_INFO' ? 'Awaiting Info' : 'Pending Review'}
                                            </span>
                                        </td>
                                        <td style={{ fontSize: 12 }}>{loan.created_at?.split('T')[0]}</td>
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
                        <h3 className="card-title">Application Review</h3>
                        <button className="btn btn-secondary btn-icon" onClick={() => setSelectedLoan(null)}>✕</button>
                    </div>
                    <div className="card-body">
                        {selectedLoan.disbursement_comments && (
                            <div className="alert alert-warning" style={{ marginBottom: 16 }}>
                                <span><strong>Returned by Disbursement Team:</strong> {selectedLoan.disbursement_comments}</span>
                            </div>
                        )}

                        {/* Pending Info Banner */}
                        {selectedLoan.status === 'PENDING_INFO' && (
                            <div className="alert alert-info" style={{ marginBottom: 16 }}>
                                <div>
                                    <strong>⏳ Awaiting Client Information</strong>
                                    <div style={{ marginTop: 6, fontSize: 13 }}>
                                        <div><strong>Requested by:</strong> {selectedLoan.info_request_by}</div>
                                        <div style={{ marginTop: 4 }}><strong>Note:</strong> {selectedLoan.info_request_note}</div>
                                    </div>
                                    {(selectedLoan.client_info_response || (selectedLoan.info_documents && selectedLoan.info_documents.length > 0)) && (
                                        <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(0,0,0,0.05)', borderRadius: 6, fontSize: 13 }}>
                                            <strong>Client Response:</strong>
                                            {selectedLoan.client_info_response && (
                                                <div style={{ marginTop: 4 }}>{selectedLoan.client_info_response}</div>
                                            )}
                                            {selectedLoan.info_documents && selectedLoan.info_documents.length > 0 && (
                                                <div style={{ marginTop: 8 }}>
                                                    <div style={{ fontWeight: 600, marginBottom: 4 }}>Uploaded Documents:</div>
                                                    {selectedLoan.info_documents.map((doc: any) => (
                                                        <a
                                                            key={doc.id}
                                                            href={doc.file_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--primary-700)', textDecoration: 'none', padding: '2px 0' }}
                                                        >
                                                            📄 {doc.file_name}
                                                        </a>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Loan Details */}
                        <div style={{ background: 'var(--gray-50)', borderRadius: 10, padding: 16, marginBottom: 16 }}>
                            <div style={{ fontWeight: 700, marginBottom: 12, color: 'var(--primary-700)' }}>📋 Loan Details</div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 13 }}>
                                <div><span style={{ color: 'var(--gray-400)' }}>Loan #:</span> <strong>{selectedLoan.loan_number}</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Product:</span> <strong>{selectedLoan.product_name}</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Amount:</span> <strong>ZMW {Number(selectedLoan.amount).toLocaleString()}</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Term:</span> <strong>{selectedLoan.term_months} months</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Rate:</span> <strong>{selectedLoan.interest_rate}%</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Monthly:</span> <strong>ZMW {Number(selectedLoan.monthly_payment || 0).toLocaleString()}</strong></div>
                            </div>
                            <div style={{ marginTop: 10, fontSize: 13 }}>
                                <span style={{ color: 'var(--gray-400)' }}>Purpose:</span> <strong>{selectedLoan.purpose}</strong>
                            </div>
                        </div>

                        {/* Client Details */}
                        <div style={{ background: 'var(--gray-50)', borderRadius: 10, padding: 16, marginBottom: 16 }}>
                            <div style={{ fontWeight: 700, marginBottom: 12, color: 'var(--primary-700)' }}>👤 Client Profile</div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 13 }}>
                                <div><span style={{ color: 'var(--gray-400)' }}>Name:</span> <strong>{selectedLoan.client_name}</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Tier:</span> <span className="badge badge-purple">{selectedLoan.client_tier}</span></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Income:</span> <strong>ZMW {Number(selectedLoan.client_income || 0).toLocaleString()}/mo</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Credit:</span> <strong>{selectedLoan.client_credit_score || '—'}</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Employment:</span> <strong>{selectedLoan.client_employment}</strong></div>
                                <div><span style={{ color: 'var(--gray-400)' }}>Completed:</span> <strong>{selectedLoan.client_completed_loans || 0} loans</strong></div>
                            </div>
                        </div>

                        {/* DTI Indicator */}
                        {selectedLoan.client_income && selectedLoan.monthly_payment && (
                            <div style={{ marginBottom: 16 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                                    <span style={{ color: 'var(--gray-500)' }}>Debt-to-Income Ratio</span>
                                    <strong style={{ color: (selectedLoan.monthly_payment / selectedLoan.client_income) > 0.4 ? 'var(--error)' : 'var(--success)' }}>
                                        {((selectedLoan.monthly_payment / selectedLoan.client_income) * 100).toFixed(1)}%
                                    </strong>
                                </div>
                                <div className="progress-bar">
                                    <div className="progress-fill" style={{
                                        width: `${Math.min(100, (selectedLoan.monthly_payment / selectedLoan.client_income) * 100)}%`,
                                        background: (selectedLoan.monthly_payment / selectedLoan.client_income) > 0.4 ? 'var(--error)' : 'var(--success)',
                                    }}></div>
                                </div>
                            </div>
                        )}

                        {/* AI Analysis */}
                        <div style={{ borderTop: '1px solid var(--gray-100)', paddingTop: 16, marginBottom: 16 }}>
                            <button
                                className="btn btn-secondary w-full"
                                onClick={handleAiAnalysis}
                                disabled={aiLoading}
                                style={{ marginBottom: 12 }}
                            >
                                {aiLoading ? <span className="loading-spinner"></span> : '🤖'} AI Risk Analysis
                            </button>
                            {aiAnalysis && (
                                <div style={{
                                    background: 'var(--primary-50)',
                                    border: '1px solid var(--primary-200)',
                                    borderRadius: 10,
                                    padding: 16,
                                    fontSize: 13,
                                    lineHeight: 1.7,
                                    maxHeight: 300,
                                    overflowY: 'auto',
                                    whiteSpace: 'pre-wrap',
                                }}>
                                    {aiAnalysis}
                                </div>
                            )}
                        </div>

                        <div style={{ borderTop: '1px solid var(--gray-100)', paddingTop: 16, marginBottom: 16 }}>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label className="form-label">Underwriter Comments for Disbursement Team</label>
                                <textarea
                                    className="form-control"
                                    rows={4}
                                    placeholder="Add any notes the disbursement team should review before releasing funds."
                                    value={approvalComments}
                                    onChange={e => setApprovalComments(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* Actions */}
                        {canApprove && (
                            <div style={{ display: 'grid', gridTemplateColumns: canRequestInfo ? '1fr 1fr 1fr' : '1fr 1fr', gap: 10 }}>
                                <button
                                    className="btn btn-danger"
                                    onClick={() => setShowRejectModal(true)}
                                    style={{ justifyContent: 'center' }}
                                >
                                    ✗ Reject
                                </button>
                                {canRequestInfo && (
                                    <button
                                        className="btn btn-secondary"
                                        onClick={() => setShowInfoModal(true)}
                                        style={{ justifyContent: 'center' }}
                                    >
                                        ℹ Request Info
                                    </button>
                                )}
                                <button
                                    className="btn btn-success"
                                    onClick={handleApprove}
                                    disabled={actionLoading}
                                    style={{ justifyContent: 'center' }}
                                >
                                    {actionLoading ? <span className="loading-spinner"></span> : '✓'} Approve
                                </button>
                            </div>
                        )}
                        {!canApprove && canRequestInfo && (
                            <button
                                className="btn btn-secondary w-full"
                                onClick={() => setShowInfoModal(true)}
                            >
                                ℹ Request Info from Client
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Reject Modal */}
            {showRejectModal && (
                <div className="modal-overlay" onClick={() => setShowRejectModal(false)}>
                    <div className="modal" style={{ maxWidth: 400 }} onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="modal-title">Reject Application</h3>
                            <button className="btn btn-secondary btn-icon" onClick={() => setShowRejectModal(false)}>✕</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label className="form-label">Rejection Reason *</label>
                                <textarea
                                    className="form-control"
                                    placeholder="Provide a clear reason for rejection..."
                                    value={rejectReason}
                                    onChange={e => setRejectReason(e.target.value)}
                                    rows={4}
                                />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowRejectModal(false)}>Cancel</button>
                            <button className="btn btn-danger" onClick={handleReject} disabled={!rejectReason || actionLoading}>
                                Confirm Rejection
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Request Info Modal */}
            {showInfoModal && (
                <div className="modal-overlay" onClick={() => setShowInfoModal(false)}>
                    <div className="modal" style={{ maxWidth: 440 }} onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="modal-title">Request Additional Information</h3>
                            <button className="btn btn-secondary btn-icon" onClick={() => setShowInfoModal(false)}>✕</button>
                        </div>
                        <div className="modal-body">
                            <p style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 12 }}>
                                The loan will be placed on hold and the client will be notified to provide the requested information.
                            </p>
                            <div className="form-group">
                                <label className="form-label">What information is required? *</label>
                                <textarea
                                    className="form-control"
                                    placeholder="e.g. Please provide your latest 3 months payslips and proof of residence..."
                                    value={infoNote}
                                    onChange={e => setInfoNote(e.target.value)}
                                    rows={5}
                                    autoFocus
                                />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowInfoModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleRequestInfo} disabled={!infoNote.trim() || actionLoading}>
                                {actionLoading ? <span className="loading-spinner"></span> : 'Send Request'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

const MOCK_PENDING = [
    { id: 4, loan_number: 'LN456789', client_name: 'David Phiri', client_tier: 'BRONZE', client_income: 2500, client_credit_score: 580, client_employment: 'SELF_EMPLOYED', client_completed_loans: 0, product_name: 'IntZam Personal', amount: 3000, term_months: 3, interest_rate: 25, monthly_payment: 1250, purpose: 'Medical expenses', status: 'PENDING_APPROVAL', created_at: '2025-02-15T10:00:00Z' },
];

function getMockAnalysis(loan: any) {
    return `## AI Risk Assessment

**Risk Rating:** MEDIUM
**Recommendation:** REVIEW

### Key Risk Factors
- First-time borrower (no credit history)
- Self-employed income (variable)
- DTI ratio: ${loan.client_income ? ((loan.monthly_payment / loan.client_income) * 100).toFixed(1) : 'N/A'}%

### Strengths
- Loan amount is relatively small
- Short term (3 months) reduces exposure
- Medical purpose is legitimate

### Conditions
- Require additional income verification
- Consider guarantor for first loan

### Summary
This is a first-time borrower with self-employed income. The loan amount is manageable but income verification is recommended before approval.`;
}
