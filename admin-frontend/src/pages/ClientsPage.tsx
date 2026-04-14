import { useState, useEffect } from 'react';
import { clientsAPI, kycAPI } from '../services/api';

const getListData = (data: any) => (
    Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
);

const formatDate = (value?: string | null) => (
    value ? new Date(`${value}T00:00:00`).toLocaleDateString() : 'N/A'
);

export default function ClientsPage() {
    const [clients, setClients] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [search, setSearch] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [showViewModal, setShowViewModal] = useState(false);
    const [viewingClient, setViewingClient] = useState<any>(null);
    const [kycSubmission, setKycSubmission] = useState<any>(null);
    const [editClient, setEditClient] = useState<any>(null);
    const [form, setForm] = useState<any>({
        name: '', email: '', phone: '', nrc_number: '', date_of_birth: '', gender: '',
        address: '', monthly_income: '', employment_status: 'EMPLOYED', employer_name: '',
        job_title: '', next_of_kin_name: '', next_of_kin_phone: '', next_of_kin_relation: ''
    });

    useEffect(() => {
        loadClients();
    }, []);

    const loadClients = async () => {
        try {
            const res = await clientsAPI.list();
            setClients(getListData(res.data));
            setError('');
        } catch (err) {
            console.error('Failed to load clients:', err);
            setClients([]);
            setError('Failed to load clients.');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            if (editClient) {
                await clientsAPI.update(editClient.id, form);
            } else {
                await clientsAPI.create(form);
            }
            setShowModal(false);
            setEditClient(null);
            loadClients();
        } catch (e: any) {
            alert(e.response?.data?.email?.[0] || 'Error saving client');
        }
    };

    const openEdit = (client: any) => {
        setEditClient(client);
        setForm({ ...client });
        setShowModal(true);
    };

    const openNew = () => {
        setEditClient(null);
        setForm({ 
            name: '', email: '', phone: '', nrc_number: '', date_of_birth: '', gender: '',
            address: '', monthly_income: '', employment_status: 'EMPLOYED', employer_name: '',
            job_title: '', next_of_kin_name: '', next_of_kin_phone: '', next_of_kin_relation: ''
        });
        setShowModal(true);
    };

    const openView = async (client: any) => {
        setViewingClient(client);
        setShowViewModal(true);
        // Load KYC submission for this client
        try {
            const res = await kycAPI.submissions();
            const submissions = getListData(res.data);
            const clientSubmission = submissions.find((s: any) => s.client === client.id);
            setKycSubmission(clientSubmission || null);
        } catch (err) {
            console.error('Failed to load KYC submission:', err);
            setKycSubmission(null);
        }
    };

    const filtered = clients.filter(c =>
        c.name?.toLowerCase().includes(search.toLowerCase()) ||
        c.email?.toLowerCase().includes(search.toLowerCase()) ||
        c.phone?.includes(search)
    );

    const tierColors: Record<string, string> = {
        BRONZE: 'badge-gray', SILVER: 'badge-info', GOLD: 'badge-warning', PLATINUM: 'badge-purple'
    };

    return (
        <div>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Clients ({filtered.length})</h3>
                    <div className="flex gap-3">
                        <div className="search-bar">
                            <span className="search-icon">🔍</span>
                            <input
                                className="form-control"
                                placeholder="Search clients..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                style={{ paddingLeft: 36, width: 240 }}
                            />
                        </div>
                        <button className="btn btn-primary" onClick={openNew}>+ New Client</button>
                    </div>
                </div>
                <div className="table-container">
                    {loading ? (
                        <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                    ) : error ? (
                        <div className="alert alert-error" style={{ margin: 16 }}>{error}</div>
                    ) : filtered.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">👥</div>
                            <h3>{clients.length === 0 ? 'No Clients Found' : 'No Matching Clients'}</h3>
                            <p>{clients.length === 0 ? 'Registered clients will appear here once their profiles are available.' : 'Try adjusting your search terms.'}</p>
                        </div>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Phone</th>
                                    <th>Income</th>
                                    <th>Tier</th>
                                    <th>KYC</th>
                                    <th>Vetting Info</th>
                                    <th>Loans</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map(client => (
                                    <tr key={client.id}>
                                        <td>
                                            <div style={{ fontWeight: 600 }}>{client.name}</div>
                                            <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{client.nrc_number}</div>
                                        </td>
                                        <td>{client.email}</td>
                                        <td>{client.phone}</td>
                                        <td>${Number(client.monthly_income || 0).toLocaleString()}</td>
                                        <td><span className={`badge ${tierColors[client.tier] || 'badge-gray'}`}>{client.tier}</span></td>
                                        <td>
                                            <span className={`badge ${client.kyc_verified ? 'badge-success' : 'badge-error'}`}>
                                                {client.kyc_verified ? '✓ Verified' : '✗ Pending'}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${client.vetting_status === 'APPROVED' || client.vetting_status === 'Verified' ? 'badge-success' : client.vetting_status === 'PENDING' ? 'badge-warning' : client.vetting_status === 'REJECTED' ? 'badge-error' : 'badge-gray'}`}>
                                                {client.vetting_status || 'Not Submitted'}
                                            </span>
                                        </td>
                                        <td>{client.completed_loans || 0}</td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 8 }}>
                                                <button className="btn btn-info btn-sm" onClick={() => openView(client)}>View</button>
                                                <button className="btn btn-secondary btn-sm" onClick={() => openEdit(client)}>Edit</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="modal-title">{editClient ? 'Edit Client' : 'New Client'}</h3>
                            <button className="btn btn-secondary btn-icon" onClick={() => setShowModal(false)}>✕</button>
                        </div>
                        <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label className="form-label">Full Name *</label>
                                    <input className="form-control" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Email *</label>
                                    <input className="form-control" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Phone *</label>
                                    <input className="form-control" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">NRC Number</label>
                                    <input className="form-control" value={form.nrc_number || ''} onChange={e => setForm({ ...form, nrc_number: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Date of Birth</label>
                                    <input className="form-control" type="date" value={form.date_of_birth || ''} onChange={e => setForm({ ...form, date_of_birth: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Gender</label>
                                    <select className="form-control" value={form.gender || ''} onChange={e => setForm({ ...form, gender: e.target.value })}>
                                        <option value="">— Select —</option>
                                        <option value="MALE">Male</option>
                                        <option value="FEMALE">Female</option>
                                        <option value="OTHER">Other</option>
                                    </select>
                                </div>
                                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                                    <label className="form-label">Residential Address</label>
                                    <textarea className="form-control" rows={2} value={form.address || ''} onChange={e => setForm({ ...form, address: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Monthly Income (ZMW)</label>
                                    <input className="form-control" type="number" value={form.monthly_income || ''} onChange={e => setForm({ ...form, monthly_income: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Employment Status</label>
                                    <select className="form-control" value={form.employment_status} onChange={e => setForm({ ...form, employment_status: e.target.value })}>
                                        <option value="EMPLOYED">Employed</option>
                                        <option value="SELF_EMPLOYED">Self Employed</option>
                                        <option value="BUSINESS_OWNER">Business Owner</option>
                                        <option value="UNEMPLOYED">Unemployed</option>
                                        <option value="RETIRED">Retired</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Employer Name</label>
                                    <input className="form-control" value={form.employer_name || ''} onChange={e => setForm({ ...form, employer_name: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Job Title</label>
                                    <input className="form-control" value={form.job_title || ''} onChange={e => setForm({ ...form, job_title: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Next of Kin Name</label>
                                    <input className="form-control" value={form.next_of_kin_name || ''} onChange={e => setForm({ ...form, next_of_kin_name: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Next of Kin Phone</label>
                                    <input className="form-control" value={form.next_of_kin_phone || ''} onChange={e => setForm({ ...form, next_of_kin_phone: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Next of Kin Relationship</label>
                                    <input className="form-control" value={form.next_of_kin_relation || ''} onChange={e => setForm({ ...form, next_of_kin_relation: e.target.value })} />
                                </div>
                            </div>
                            {editClient && (
                                <div className="form-group" style={{ marginTop: 16 }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                        <input type="checkbox" checked={form.kyc_verified} onChange={e => setForm({ ...form, kyc_verified: e.target.checked })} />
                                        <span className="form-label" style={{ margin: 0 }}>KYC Verified</span>
                                    </label>
                                </div>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleSave}>Save Client</button>
                        </div>
                    </div>
                </div>
            )}

            {showViewModal && viewingClient && (
                <div className="modal-overlay" onClick={() => setShowViewModal(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 800 }}>
                        <div className="modal-header">
                            <h3 className="modal-title">Client Details - {viewingClient.name}</h3>
                            <button className="btn btn-secondary btn-icon" onClick={() => setShowViewModal(false)}>✕</button>
                        </div>
                        <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                            {/* Basic Information */}
                            <div className="card" style={{ marginBottom: 20 }}>
                                <div className="card-header">
                                    <h4 style={{ margin: 0, fontSize: 16 }}>Basic Information</h4>
                                </div>
                                <div className="card-body">
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Full Name</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.name}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>NRC Number</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.nrc_number || 'N/A'}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Email</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.email}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Phone</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.phone}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Date of Birth</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{formatDate(viewingClient.date_of_birth)}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Gender</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.gender || 'N/A'}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Monthly Income</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>ZMW {Number(viewingClient.monthly_income || 0).toLocaleString()}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Employment Status</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.employment_status}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Tier</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>
                                                <span className={`badge ${tierColors[viewingClient.tier] || 'badge-gray'}`}>{viewingClient.tier}</span>
                                            </div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>KYC Status</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>
                                                <span className={`badge ${viewingClient.kyc_verified ? 'badge-success' : 'badge-error'}`}>
                                                    {viewingClient.kyc_verified ? '✓ Verified' : '✗ Pending'}
                                                </span>
                                            </div>
                                        </div>
                                        <div style={{ gridColumn: '1 / -1' }}>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Residential Address</label>
                                            <div style={{ fontSize: 14, marginTop: 4, whiteSpace: 'pre-wrap' }}>{viewingClient.address || 'N/A'}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="card" style={{ marginBottom: 20 }}>
                                <div className="card-header">
                                    <h4 style={{ margin: 0, fontSize: 16 }}>Employment Information</h4>
                                </div>
                                <div className="card-body">
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Employer Name</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.employer_name || 'N/A'}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Job Title</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.job_title || 'N/A'}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Next of Kin */}
                            <div className="card" style={{ marginBottom: 20 }}>
                                <div className="card-header">
                                    <h4 style={{ margin: 0, fontSize: 16 }}>Next of Kin</h4>
                                </div>
                                <div className="card-body">
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Name</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.next_of_kin_name || 'N/A'}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Phone</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.next_of_kin_phone || 'N/A'}</div>
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Relationship</label>
                                            <div style={{ fontSize: 14, marginTop: 4 }}>{viewingClient.next_of_kin_relation || 'N/A'}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* KYC Submission */}
                            <div className="card">
                                <div className="card-header">
                                    <h4 style={{ margin: 0, fontSize: 16 }}>Additional KYC Builder Information</h4>
                                </div>
                                <div className="card-body">
                                    {kycSubmission ? (
                                        <div>
                                            <div style={{ marginBottom: 16 }}>
                                                <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Status</label>
                                                <div style={{ fontSize: 14, marginTop: 4 }}>
                                                    <span className={`badge ${kycSubmission.status === 'APPROVED' ? 'badge-success' : kycSubmission.status === 'REJECTED' ? 'badge-error' : 'badge-warning'}`}>
                                                        {kycSubmission.status}
                                                    </span>
                                                </div>
                                            </div>
                                            <div style={{ marginBottom: 16 }}>
                                                <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>Submitted At</label>
                                                <div style={{ fontSize: 14, marginTop: 4 }}>{new Date(kycSubmission.created_at).toLocaleString()}</div>
                                            </div>
                                            {kycSubmission.field_values && kycSubmission.field_values.length > 0 && (
                                                <div>
                                                    <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600, marginBottom: 12, display: 'block' }}>Submitted Information</label>
                                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                                        {kycSubmission.field_values.map((fv: any) => (
                                                            <div key={fv.id}>
                                                                <label style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 600 }}>{fv.field_label}</label>
                                                                <div style={{ fontSize: 14, marginTop: 4 }}>
                                                                    {fv.field_type === 'FILE' ? (
                                                                        fv.value_file ? <a href={fv.value_file} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-secondary">View File</a> : 'No file'
                                                                    ) : (
                                                                        fv.value_text || 'N/A'
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div style={{ textAlign: 'center', padding: 20, color: 'var(--gray-400)' }}>
                                            No KYC submission found
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowViewModal(false)}>Close</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
