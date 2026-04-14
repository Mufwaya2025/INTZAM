import { useState, useEffect } from 'react';
import { kycAPI } from '../services/api';

const getListData = (data: any) => (
    Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
);

const formatDate = (value?: string | null) => (
    value ? new Date(`${value}T00:00:00`).toLocaleDateString() : 'N/A'
);

interface KYCSubmissionsPageProps {
    userPermissions?: string[];
}

export default function KYCSubmissionsPage({ userPermissions = [] }: KYCSubmissionsPageProps) {
    const canReview = userPermissions.includes('review_kyc_submissions');
    const [submissions, setSubmissions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedSub, setSelectedSub] = useState<any>(null);
    const [actionLoading, setActionLoading] = useState(false);
    const [rejectionNotes, setRejectionNotes] = useState('');

    const registrationProfile = selectedSub?.client_details;

    const loadData = () => {
        setLoading(true);
        kycAPI.submissions()
            .then(res => {
                setSubmissions(getListData(res.data));
                setError('');
            })
            .catch((err) => {
                console.error('Failed to load KYC submissions:', err);
                setSubmissions([]);
                setError('Failed to load KYC submissions.');
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleReview = async (status: 'APPROVED' | 'REJECTED') => {
        if (!selectedSub) return;
        if (status === 'REJECTED' && !rejectionNotes.trim()) {
            alert('Please provide rejection notes.');
            return;
        }

        setActionLoading(true);
        try {
            await kycAPI.reviewSubmission(selectedSub.id, {
                status,
                reviewer_notes: rejectionNotes
            });
            setSelectedSub(null);
            setRejectionNotes('');
            loadData();
        } catch (e: any) {
            const msg = e?.response?.data?.detail || e?.response?.data?.error || 'Failed to process review.';
            alert(msg);
        } finally {
            setActionLoading(false);
        }
    };

    return (
        <div>
            <div className="flex justify-between items-center" style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 24, fontWeight: 700 }}>Client KYC Reviews</h1>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>Loading submissions...</div>
            ) : error ? (
                <div className="alert alert-error">{error}</div>
            ) : submissions.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-state-icon">🔍</div>
                    <h3>No Submissions found</h3>
                    <p>There are currently no KYC reviews pending.</p>
                </div>
            ) : (
                <div className="card">
                    <div className="card-table">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Client</th>
                                    <th>Date Submitted</th>
                                    <th>Status</th>
                                    <th>Notes</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {submissions.map(sub => (
                                    <tr key={sub.id}>
                                        <td><strong>{sub.client_name}</strong></td>
                                        <td>{new Date(sub.created_at).toLocaleDateString()}</td>
                                        <td>
                                            <span className={`badge ${sub.status === 'APPROVED' ? 'badge-success' : sub.status === 'REJECTED' ? 'badge-error' : 'badge-warning'}`}>
                                                {sub.status}
                                            </span>
                                        </td>
                                        <td><span className="truncate" style={{ maxWidth: 200 }}>{sub.reviewer_notes || '—'}</span></td>
                                        <td>
                                            <button className="btn btn-sm btn-secondary" onClick={() => setSelectedSub(sub)}>Review Docs</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Review Modal */}
            {selectedSub && (
                <div className="modal-backdrop">
                    <div className="modal-content animate-in" style={{ maxWidth: 700 }}>
                        <div className="modal-header">
                            <h2 className="modal-title">Review KYC: {selectedSub.client_name}</h2>
                            <button className="modal-close" onClick={() => setSelectedSub(null)}>×</button>
                        </div>
                        <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                            {registrationProfile && (
                                <div style={{ marginBottom: 24 }}>
                                    <h3 style={{ fontSize: 16, marginBottom: 12 }}>Registration Information</h3>
                                    <div style={{ display: 'grid', gap: 16 }}>
                                        <div style={{ background: 'var(--gray-50)', padding: 16, borderRadius: 8 }}>
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Full Name</div>
                                                    <div style={{ marginTop: 4, color: 'var(--gray-900)', fontWeight: 600 }}>{registrationProfile.name || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Email</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.email || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Phone</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.phone || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>NRC Number</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.nrc_number || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Date of Birth</div>
                                                    <div style={{ marginTop: 4 }}>{formatDate(registrationProfile.date_of_birth)}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Employment Status</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.employment_status || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Monthly Income</div>
                                                    <div style={{ marginTop: 4 }}>ZMW {Number(registrationProfile.monthly_income || 0).toLocaleString()}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Employer Name</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.employer_name || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Job Title</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.job_title || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Next of Kin Name</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.next_of_kin_name || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Next of Kin Phone</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.next_of_kin_phone || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Next of Kin Relationship</div>
                                                    <div style={{ marginTop: 4 }}>{registrationProfile.next_of_kin_relation || 'N/A'}</div>
                                                </div>
                                                <div style={{ gridColumn: '1 / -1' }}>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Residential Address</div>
                                                    <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{registrationProfile.address || 'N/A'}</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div style={{ marginBottom: 24 }}>
                                <h3 style={{ fontSize: 16, marginBottom: 12 }}>Additional KYC Builder Information</h3>
                                <div style={{ display: 'grid', gap: 16 }}>
                                    {selectedSub.field_values?.map((fv: any) => (
                                        <div key={fv.id} style={{ background: 'var(--gray-50)', padding: 16, borderRadius: 8 }}>
                                            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 4 }}>{fv.field_label} ({fv.field_type})</div>
                                            {fv.field_type === 'FILE' ? (
                                                <a href={fv.value_file} target="_blank" rel="noreferrer" style={{ color: 'var(--primary-600)', fontWeight: 600 }}>Download/View Attachment</a>
                                            ) : (
                                                <div style={{ fontWeight: 600, color: 'var(--gray-900)' }}>{fv.value_text || '—'}</div>
                                            )}
                                        </div>
                                    ))}
                                    {(!selectedSub.field_values || selectedSub.field_values.length === 0) && (
                                        <div style={{ color: 'var(--gray-500)' }}>No values provided.</div>
                                    )}
                                </div>
                            </div>
                            {selectedSub.status === 'PENDING' && canReview && (
                                <div className="form-group" style={{ borderTop: '1px solid var(--gray-200)', paddingTop: 16 }}>
                                    <label className="form-label">Reviewer Notes (Required for Rejection)</label>
                                    <textarea className="form-control" rows={3} value={rejectionNotes} onChange={e => setRejectionNotes(e.target.value)} />
                                </div>
                            )}
                        </div>
                        <div className="modal-footer" style={{ justifyContent: (selectedSub.status === 'PENDING' && canReview) ? 'space-between' : 'flex-end' }}>
                            {selectedSub.status === 'PENDING' && canReview ? (
                                <>
                                    <button className="btn btn-danger" onClick={() => handleReview('REJECTED')} disabled={actionLoading}>Reject Request</button>
                                    <button className="btn btn-success" onClick={() => handleReview('APPROVED')} disabled={actionLoading}>Approve & Verify KYC</button>
                                </>
                            ) : (
                                <button className="btn btn-secondary" onClick={() => setSelectedSub(null)}>Close</button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
