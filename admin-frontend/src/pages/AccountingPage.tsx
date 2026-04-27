import { useState, useEffect } from 'react';
import { accountingAPI, loansAPI } from '../services/api';
import { formatMoney } from '../utils/format';

interface AccountingPageProps {
    initialTab?: 'disbursements' | 'trial-balance' | 'accounts' | 'journal';
}

type AccountingTab = NonNullable<AccountingPageProps['initialTab']>;

const formatDate = (value?: string | null) => (
    value ? new Date(`${value}T00:00:00`).toLocaleDateString() : 'N/A'
);

export default function AccountingPage({ initialTab = 'trial-balance' }: AccountingPageProps) {
    const [activeTab, setActiveTab] = useState(initialTab);
    const [trialBalance, setTrialBalance] = useState<any>(null);
    const [accounts, setAccounts] = useState<any[]>([]);
    const [journal, setJournal] = useState<any[]>([]);
    const [disbursementQueue, setDisbursementQueue] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedLoan, setSelectedLoan] = useState<any>(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [modalActionLoading, setModalActionLoading] = useState(false);
    const [returnReason, setReturnReason] = useState('');

    useEffect(() => {
        if (activeTab === 'disbursements') loadDisbursementQueue();
        else if (activeTab === 'trial-balance') loadTrialBalance();
        else if (activeTab === 'accounts') loadAccounts();
        else if (activeTab === 'journal') loadJournal();
    }, [activeTab]);

    useEffect(() => {
        setActiveTab(initialTab);
    }, [initialTab]);

    const loadDisbursementQueue = async () => {
        setLoading(true);
        try {
            const res = await loansAPI.list({ status: 'APPROVED' });
            setDisbursementQueue(res.data.results || res.data);
        } catch {
            setDisbursementQueue(MOCK_DISBURSEMENT_QUEUE);
        } finally {
            setLoading(false);
        }
    };

    const openLoanReview = async (loan: any) => {
        setSelectedLoan(null);
        setReturnReason('');
        setDetailLoading(true);
        try {
            const res = await loansAPI.get(loan.id);
            setSelectedLoan(res.data);
        } catch (e: any) {
            setSelectedLoan(loan);
        } finally {
            setDetailLoading(false);
        }
    };

    const closeLoanReview = () => {
        setSelectedLoan(null);
        setReturnReason('');
        setDetailLoading(false);
    };

    const handleDisburse = async () => {
        if (!selectedLoan) return;
        setModalActionLoading(true);
        try {
            await loansAPI.disburse(selectedLoan.id);
            closeLoanReview();
            await loadDisbursementQueue();
            loadJournal();
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error disbursing loan');
        } finally {
            setModalActionLoading(false);
        }
    };

    const handleSendBack = async () => {
        if (!selectedLoan) return;
        if (!returnReason.trim()) {
            alert('Please provide comments before sending the loan back to underwriting.');
            return;
        }

        setModalActionLoading(true);
        try {
            await loansAPI.returnToUnderwriter(selectedLoan.id, returnReason.trim());
            closeLoanReview();
            await loadDisbursementQueue();
        } catch (e: any) {
            alert(e.response?.data?.error || 'Error sending loan back to underwriting');
        } finally {
            setModalActionLoading(false);
        }
    };

    const loadTrialBalance = async () => {
        setLoading(true);
        try {
            const res = await accountingAPI.trialBalance();
            setTrialBalance(res.data);
        } catch {
            setTrialBalance(MOCK_TRIAL_BALANCE);
        } finally {
            setLoading(false);
        }
    };

    const loadAccounts = async () => {
        setLoading(true);
        try {
            const res = await accountingAPI.accounts();
            setAccounts(res.data.results || res.data);
        } catch {
            setAccounts(MOCK_ACCOUNTS);
        } finally {
            setLoading(false);
        }
    };

    const loadJournal = async () => {
        setLoading(true);
        try {
            const res = await accountingAPI.journal();
            setJournal(res.data.results || res.data);
        } catch {
            setJournal([]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <div className="tabs">
                {([
                    { id: 'disbursements', label: `Disbursements Queue${disbursementQueue.length ? ` (${disbursementQueue.length})` : ''}` },
                    { id: 'trial-balance', label: 'Trial Balance' },
                    { id: 'accounts', label: 'Chart of Accounts' },
                    { id: 'journal', label: 'Journal Entries' },
                ] as { id: AccountingTab; label: string }[]).map(tab => (
                    <div key={tab.id} className={`tab ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>
                        {tab.label}
                    </div>
                ))}
            </div>

            {loading && <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>}

            {!loading && activeTab === 'disbursements' && (
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Disbursements Queue ({disbursementQueue.length})</h3>
                        <span className="badge badge-success">Final Accountant Action</span>
                    </div>
                    {disbursementQueue.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">ZMW</div>
                            <h3>No Pending Disbursements</h3>
                            <p>Approved loans waiting for payout will appear here.</p>
                        </div>
                    ) : (
                        <div className="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Loan #</th>
                                        <th>Client</th>
                                        <th>Product</th>
                                        <th>Approved By</th>
                                        <th>Amount</th>
                                        <th>Total Repayable</th>
                                        <th>Applied</th>
                                        <th>Review</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {disbursementQueue.map(loan => (
                                        <tr key={loan.id}>
                                            <td><strong>{loan.loan_number}</strong></td>
                                            <td>{loan.client_name || loan.client}</td>
                                            <td>{loan.product_name || loan.product}</td>
                                            <td>{loan.approved_by || '—'}</td>
                                            <td><strong>{formatMoney(loan.amount)}</strong></td>
                                            <td>{formatMoney(loan.total_repayable)}</td>
                                            <td>{loan.created_at?.split('T')[0] || '—'}</td>
                                            <td>
                                                <button
                                                    className="btn btn-secondary btn-sm"
                                                    onClick={() => openLoanReview(loan)}
                                                >
                                                    View
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {(detailLoading || selectedLoan) && (
                <div className="modal-backdrop">
                    <div className="modal-content animate-in" style={{ maxWidth: 820 }}>
                        <div className="modal-header">
                            <h2 className="modal-title">
                                {detailLoading ? 'Loading disbursement review...' : `Disbursement Review: ${selectedLoan?.loan_number}`}
                            </h2>
                            <button className="modal-close" onClick={closeLoanReview}>×</button>
                        </div>
                        <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                            {detailLoading ? (
                                <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
                                    <div className="loading-spinner" style={{ width: 32, height: 32 }}></div>
                                </div>
                            ) : selectedLoan && (
                                <>
                                    <div style={{ background: 'var(--gray-50)', borderRadius: 10, padding: 16, marginBottom: 20 }}>
                                        <div style={{ fontWeight: 700, marginBottom: 12, color: 'var(--primary-700)' }}>Loan Approval Summary</div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, fontSize: 13 }}>
                                            <div><span style={{ color: 'var(--gray-400)' }}>Client:</span> <strong>{selectedLoan.client_name}</strong></div>
                                            <div><span style={{ color: 'var(--gray-400)' }}>Product:</span> <strong>{selectedLoan.product_name}</strong></div>
                                            <div><span style={{ color: 'var(--gray-400)' }}>Amount:</span> <strong>{formatMoney(selectedLoan.amount)}</strong></div>
                                            <div><span style={{ color: 'var(--gray-400)' }}>Total Repayable:</span> <strong>{formatMoney(selectedLoan.total_repayable)}</strong></div>
                                            <div><span style={{ color: 'var(--gray-400)' }}>Term:</span> <strong>{selectedLoan.term_months} months</strong></div>
                                            <div><span style={{ color: 'var(--gray-400)' }}>Approved By:</span> <strong>{selectedLoan.approved_by || '—'}</strong></div>
                                        </div>
                                        <div style={{ marginTop: 14 }}>
                                            <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Underwriter Comments</div>
                                            <div style={{ marginTop: 6, whiteSpace: 'pre-wrap', color: 'var(--gray-900)' }}>
                                                {selectedLoan.underwriter_comments || 'No underwriter comments were provided.'}
                                            </div>
                                        </div>
                                    </div>

                                    {selectedLoan.client_details && (
                                        <div style={{ marginBottom: 24 }}>
                                            <h3 style={{ fontSize: 16, marginBottom: 12 }}>Customer Registration Information</h3>
                                            <div style={{ background: 'var(--gray-50)', padding: 16, borderRadius: 8 }}>
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Full Name</div>
                                                        <div style={{ marginTop: 4, fontWeight: 600 }}>{selectedLoan.client_details.name || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Email</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.email || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Phone</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.phone || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>NRC Number</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.nrc_number || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Date of Birth</div>
                                                        <div style={{ marginTop: 4 }}>{formatDate(selectedLoan.client_details.date_of_birth)}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Employment Status</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.employment_status || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Monthly Income</div>
                                                        <div style={{ marginTop: 4 }}>{formatMoney(selectedLoan.client_details.monthly_income)}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Employer Name</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.employer_name || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Job Title</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.job_title || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Next of Kin Name</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.next_of_kin_name || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Next of Kin Phone</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.next_of_kin_phone || 'N/A'}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Next of Kin Relationship</div>
                                                        <div style={{ marginTop: 4 }}>{selectedLoan.client_details.next_of_kin_relation || 'N/A'}</div>
                                                    </div>
                                                    <div style={{ gridColumn: '1 / -1' }}>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Residential Address</div>
                                                        <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{selectedLoan.client_details.address || 'N/A'}</div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    <div style={{ marginBottom: 24 }}>
                                        <h3 style={{ fontSize: 16, marginBottom: 12 }}>Customer KYC Information</h3>
                                        {selectedLoan.latest_kyc_submission ? (
                                            <>
                                                <div style={{ marginBottom: 12 }}>
                                                    <span className={`badge ${
                                                        selectedLoan.latest_kyc_submission.status === 'APPROVED'
                                                            ? 'badge-success'
                                                            : selectedLoan.latest_kyc_submission.status === 'REJECTED'
                                                                ? 'badge-error'
                                                                : 'badge-warning'
                                                    }`}>
                                                        {selectedLoan.latest_kyc_submission.status}
                                                    </span>
                                                </div>
                                                <div style={{ display: 'grid', gap: 16 }}>
                                                    {selectedLoan.latest_kyc_submission.field_values?.map((fieldValue: any) => (
                                                        <div key={fieldValue.id} style={{ background: 'var(--gray-50)', padding: 16, borderRadius: 8 }}>
                                                            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 4 }}>
                                                                {fieldValue.field_label} ({fieldValue.field_type})
                                                            </div>
                                                            {fieldValue.field_type === 'FILE' ? (
                                                                <a
                                                                    href={fieldValue.value_file}
                                                                    target="_blank"
                                                                    rel="noreferrer"
                                                                    style={{ color: 'var(--primary-600)', fontWeight: 600 }}
                                                                >
                                                                    Download/View Attachment
                                                                </a>
                                                            ) : (
                                                                <div style={{ fontWeight: 600, color: 'var(--gray-900)' }}>{fieldValue.value_text || '—'}</div>
                                                            )}
                                                        </div>
                                                    ))}
                                                    {(!selectedLoan.latest_kyc_submission.field_values || selectedLoan.latest_kyc_submission.field_values.length === 0) && (
                                                        <div style={{ color: 'var(--gray-500)' }}>No additional KYC builder fields were submitted.</div>
                                                    )}
                                                </div>
                                            </>
                                        ) : (
                                            <div style={{ color: 'var(--gray-500)' }}>No KYC submission is attached to this customer record.</div>
                                        )}
                                    </div>

                                    <div className="form-group" style={{ marginBottom: 0 }}>
                                        <label className="form-label">Disbursement Team Comments</label>
                                        <textarea
                                            className="form-control"
                                            rows={4}
                                            placeholder="If this needs to go back to underwriting, explain what must be corrected."
                                            value={returnReason}
                                            onChange={e => setReturnReason(e.target.value)}
                                        />
                                    </div>
                                </>
                            )}
                        </div>
                        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
                            <button className="btn btn-danger" onClick={handleSendBack} disabled={detailLoading || modalActionLoading}>
                                {modalActionLoading ? <span className="loading-spinner"></span> : 'Send Back to Underwriter'}
                            </button>
                            <div style={{ display: 'flex', gap: 12 }}>
                                <button className="btn btn-secondary" onClick={closeLoanReview} disabled={modalActionLoading}>Close</button>
                                <button className="btn btn-success" onClick={handleDisburse} disabled={detailLoading || modalActionLoading}>
                                    {modalActionLoading ? <span className="loading-spinner"></span> : 'Disburse Loan'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {!loading && activeTab === 'trial-balance' && trialBalance && (
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Trial Balance</h3>
                        <span className="badge badge-purple">As of today</span>
                    </div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Code</th>
                                    <th>Account Name</th>
                                    <th>Type</th>
                                    <th style={{ textAlign: 'right' }}>Debit</th>
                                    <th style={{ textAlign: 'right' }}>Credit</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trialBalance.accounts?.map((acc: any) => (
                                    <tr key={acc.code}>
                                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{acc.code}</td>
                                        <td>{acc.name}</td>
                                        <td><span className={`badge ${acc.type === 'ASSET' ? 'badge-success' : acc.type === 'LIABILITY' ? 'badge-error' : acc.type === 'INCOME' ? 'badge-purple' : 'badge-warning'}`}>{acc.type}</span></td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                            {acc.debit > 0 ? formatMoney(acc.debit) : '—'}
                                        </td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                            {acc.credit > 0 ? formatMoney(acc.credit) : '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot>
                                <tr style={{ background: 'var(--primary-50)', fontWeight: 700 }}>
                                    <td colSpan={3} style={{ padding: '14px 16px' }}>TOTALS</td>
                                    <td style={{ textAlign: 'right', padding: '14px 16px', fontFamily: 'monospace', color: 'var(--primary-700)' }}>
                                        {formatMoney(trialBalance.total_debit)}
                                    </td>
                                    <td style={{ textAlign: 'right', padding: '14px 16px', fontFamily: 'monospace', color: 'var(--primary-700)' }}>
                                        {formatMoney(trialBalance.total_credit)}
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            )}

            {!loading && activeTab === 'accounts' && (
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Chart of Accounts ({accounts.length})</h3>
                    </div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Code</th>
                                    <th>Account Name</th>
                                    <th>Type</th>
                                    <th>Category</th>
                                    <th style={{ textAlign: 'right' }}>Balance</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {accounts.map(acc => (
                                    <tr key={acc.id}>
                                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{acc.code}</td>
                                        <td>{acc.name}</td>
                                        <td><span className={`badge ${acc.account_type === 'ASSET' ? 'badge-success' : acc.account_type === 'LIABILITY' ? 'badge-error' : acc.account_type === 'INCOME' ? 'badge-purple' : 'badge-warning'}`}>{acc.account_type}</span></td>
                                        <td><span className="badge badge-gray">{acc.category}</span></td>
                                        <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                                            {formatMoney(acc.balance)}
                                        </td>
                                        <td><span className={`badge ${acc.is_active ? 'badge-success' : 'badge-error'}`}>{acc.is_active ? 'Active' : 'Inactive'}</span></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {!loading && activeTab === 'journal' && (
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Journal Entries</h3>
                    </div>
                    {journal.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">JE</div>
                            <h3>No Journal Entries</h3>
                            <p>Journal entries are created automatically when loans are disbursed and repaid.</p>
                        </div>
                    ) : (
                        <div className="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Reference</th>
                                        <th>Description</th>
                                        <th>Date</th>
                                        <th style={{ textAlign: 'right' }}>Debit</th>
                                        <th style={{ textAlign: 'right' }}>Credit</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {journal.map(entry => (
                                        <tr key={entry.id}>
                                            <td style={{ fontFamily: 'monospace' }}>{entry.reference_id || `JE-${entry.id}`}</td>
                                            <td>{entry.description}</td>
                                            <td>{entry.date}</td>
                                            <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{formatMoney(entry.total_debit)}</td>
                                            <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{formatMoney(entry.total_credit)}</td>
                                            <td><span className={`badge ${entry.is_posted ? 'badge-success' : 'badge-warning'}`}>{entry.is_posted ? 'Posted' : 'Draft'}</span></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

const MOCK_TRIAL_BALANCE = {
    accounts: [
        { code: '1001', name: 'Cash and Bank', type: 'ASSET', debit: 250000, credit: 0 },
        { code: '1100', name: 'Loan Portfolio', type: 'ASSET', debit: 980000, credit: 0 },
        { code: '1200', name: 'Interest Receivable', type: 'ASSET', debit: 45000, credit: 0 },
        { code: '2001', name: 'Customer Deposits', type: 'LIABILITY', debit: 0, credit: 120000 },
        { code: '2100', name: 'Borrowings', type: 'LIABILITY', debit: 0, credit: 500000 },
        { code: '3001', name: 'Share Capital', type: 'EQUITY', debit: 0, credit: 500000 },
        { code: '3100', name: 'Retained Earnings', type: 'EQUITY', debit: 0, credit: 100000 },
        { code: '4001', name: 'Interest Income', type: 'INCOME', debit: 0, credit: 85000 },
        { code: '4100', name: 'Fee Income', type: 'INCOME', debit: 0, credit: 12000 },
        { code: '5001', name: 'Interest Expense', type: 'EXPENSE', debit: 18000, credit: 0 },
        { code: '5100', name: 'Operating Expenses', type: 'EXPENSE', debit: 24000, credit: 0 },
    ],
    total_debit: 1317000,
    total_credit: 1317000,
};

const MOCK_ACCOUNTS = [
    { id: 1, code: '1001', name: 'Cash and Bank', account_type: 'ASSET', category: 'BS', balance: 250000, is_active: true },
    { id: 2, code: '1100', name: 'Loan Portfolio', account_type: 'ASSET', category: 'BS', balance: 980000, is_active: true },
    { id: 3, code: '4001', name: 'Interest Income', account_type: 'INCOME', category: 'PL', balance: 85000, is_active: true },
    { id: 4, code: '5001', name: 'Interest Expense', account_type: 'EXPENSE', category: 'PL', balance: 18000, is_active: true },
];

const MOCK_DISBURSEMENT_QUEUE = [
    {
        id: 4,
        loan_number: 'LN456789',
        client_name: 'David Phiri',
        product_name: 'IntZam Personal',
        approved_by: 'Underwriter One',
        amount: 3000,
        total_repayable: 3750,
        created_at: '2025-02-15T10:00:00Z',
    },
];
