import { useState, useEffect, useRef } from 'react';
import { qualifiedBaseAPI, kycAPI, productsAPI } from '../services/api';

export default function QualifiedBasePage() {
    const [records, setRecords] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Modal state
    const [modalOpen, setModalOpen] = useState(false);
    const [step, setStep] = useState<1 | 2>(1);
    const [eligibleClients, setEligibleClients] = useState<any[]>([]);
    const [eligibleLoading, setEligibleLoading] = useState(false);
    const [clientSearch, setClientSearch] = useState('');
    const [selectedClient, setSelectedClient] = useState<any>(null);
    const [kycSubmission, setKycSubmission] = useState<any>(null);
    const [products, setProducts] = useState<any[]>([]);
    const [step2Loading, setStep2Loading] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<any>(null);
    const [amount, setAmount] = useState('');
    const [reason, setReason] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => { loadRecords(); }, []);

    const loadRecords = async () => {
        try {
            const res = await qualifiedBaseAPI.list();
            setRecords(res.data.results || res.data);
        } finally {
            setLoading(false);
        }
    };

    const openModal = async () => {
        setStep(1);
        setSelectedClient(null);
        setKycSubmission(null);
        setProducts([]);
        setSelectedProduct(null);
        setAmount('');
        setReason('');
        setClientSearch('');
        setModalOpen(true);
        setEligibleLoading(true);
        try {
            const res = await qualifiedBaseAPI.eligibleClients();
            setEligibleClients(res.data);
        } catch {
            setEligibleClients([]);
        } finally {
            setEligibleLoading(false);
        }
    };

    const closeModal = () => {
        setModalOpen(false);
        setSelectedClient(null);
        setKycSubmission(null);
        setProducts([]);
        setSelectedProduct(null);
        setAmount('');
        setReason('');
        setClientSearch('');
    };

    const selectClient = async (client: any) => {
        setSelectedClient(client);
        setSelectedProduct(null);
        setAmount('');
        setReason('');
        setStep(2);
        setStep2Loading(true);
        try {
            const [subsRes, prodsRes] = await Promise.all([
                kycAPI.submissions(),
                productsAPI.list(),
            ]);
            const allSubs = subsRes.data?.results || subsRes.data || [];
            const approved = allSubs.find((s: any) => s.client === client.id && s.status === 'APPROVED');
            setKycSubmission(approved || null);
            setProducts(prodsRes.data?.results || prodsRes.data || []);
        } catch {
            setKycSubmission(null);
            setProducts([]);
        } finally {
            setStep2Loading(false);
        }
    };

    const handleProductSelect = (product: any) => {
        if (selectedProduct?.id === product.id) {
            setSelectedProduct(null);
        } else {
            setSelectedProduct(product);
            // Auto-suggest amount as the product's max if not yet set
            if (!amount) {
                setAmount(String(product.max_amount));
            }
        }
    };

    const handleSave = async () => {
        if (!selectedClient || !amount || !reason.trim()) return;
        setSaving(true);
        try {
            await qualifiedBaseAPI.addFromClient({
                client_id: selectedClient.id,
                amount_qualified_for: Number(amount),
                reason: reason.trim(),
                product_name: selectedProduct?.name || null,
            });
            closeModal();
            loadRecords();
        } catch (e: any) {
            alert(e.response?.data?.error || 'Failed to add client to Qualified Base.');
        } finally {
            setSaving(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        setLoading(true);
        try {
            const res = await qualifiedBaseAPI.upload(formData);
            alert(res.data.message || 'Upload complete');
            loadRecords();
        } catch (err: any) {
            alert(err.response?.data?.error || 'Upload failed');
        } finally {
            setLoading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const filtered = records.filter(c =>
        c.first_name?.toLowerCase().includes(search.toLowerCase()) ||
        c.last_name?.toLowerCase().includes(search.toLowerCase()) ||
        c.nrc_number?.includes(search)
    );

    const filteredEligible = eligibleClients.filter(c =>
        c.name?.toLowerCase().includes(clientSearch.toLowerCase()) ||
        c.nrc_number?.includes(clientSearch) ||
        c.phone?.includes(clientSearch)
    );

    // Products the client can access with the given cap
    const qualifyingProducts = products.filter(p =>
        !amount || Number(amount) >= Number(p.min_amount)
    );

    return (
        <div>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Qualified Base ({filtered.length})</h3>
                    <div className="flex gap-3">
                        <div className="search-bar">
                            <span className="search-icon">🔍</span>
                            <input
                                className="form-control"
                                placeholder="Search by NRC or Name..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                style={{ paddingLeft: 36, width: 240 }}
                            />
                        </div>
                        <input type="file" accept=".csv" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} />
                        <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()}>Upload CSV</button>
                        <button className="btn btn-primary" onClick={openModal}>+ Add Manual</button>
                    </div>
                </div>
                <div className="table-container">
                    {loading ? (
                        <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Date Added</th>
                                    <th>First Name</th>
                                    <th>Last Name</th>
                                    <th>Phone</th>
                                    <th>NRC</th>
                                    <th>Approved Cap</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.length === 0 ? (
                                    <tr><td colSpan={6} style={{ textAlign: 'center', padding: '40px 0' }}>No records found</td></tr>
                                ) : filtered.map((record, i) => (
                                    <tr key={record.id || i}>
                                        <td>{new Date(record.date_qualified).toLocaleDateString()}</td>
                                        <td style={{ fontWeight: 600 }}>{record.first_name}</td>
                                        <td style={{ fontWeight: 600 }}>{record.last_name}</td>
                                        <td>{record.phone_number}</td>
                                        <td style={{ color: 'var(--primary-600)', fontWeight: 500 }}>{record.nrc_number}</td>
                                        <td>ZMW {Number(record.amount_qualified_for).toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {modalOpen && (
                <div className="modal-backdrop">
                    <div className="modal-content animate-in" style={{ maxWidth: step === 1 ? 560 : 760 }}>
                        <div className="modal-header">
                            <div>
                                <h2 className="modal-title">
                                    {step === 1 ? 'Select KYC-Verified Client' : 'Review & Qualify'}
                                </h2>
                                <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 2 }}>
                                    Step {step} of 2 — {step === 1
                                        ? 'Only clients with approved KYC are shown'
                                        : `Reviewing: ${selectedClient?.name}`}
                                </div>
                            </div>
                            <button className="modal-close" onClick={closeModal}>×</button>
                        </div>

                        {step === 1 ? (
                            <>
                                <div className="modal-body">
                                    <div style={{ marginBottom: 12 }}>
                                        <input
                                            className="form-control"
                                            placeholder="Search by name, NRC, or phone..."
                                            value={clientSearch}
                                            onChange={e => setClientSearch(e.target.value)}
                                            autoFocus
                                        />
                                    </div>
                                    {eligibleLoading ? (
                                        <div style={{ textAlign: 'center', padding: 32 }}>
                                            <div className="loading-spinner" style={{ width: 28, height: 28, margin: '0 auto' }}></div>
                                        </div>
                                    ) : filteredEligible.length === 0 ? (
                                        <div className="empty-state" style={{ padding: '32px 0' }}>
                                            <div className="empty-state-icon">✅</div>
                                            <h3>{clientSearch ? 'No matches found' : 'No eligible clients'}</h3>
                                            <p>{clientSearch ? 'Try a different search term.' : 'All KYC-verified clients are already in the Qualified Base, or no clients have approved KYC yet.'}</p>
                                        </div>
                                    ) : (
                                        <div style={{ maxHeight: 360, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                                            {filteredEligible.map(client => (
                                                <div
                                                    key={client.id}
                                                    onClick={() => selectClient(client)}
                                                    style={{
                                                        padding: '12px 16px',
                                                        border: '1.5px solid var(--gray-200)',
                                                        borderRadius: 8,
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        justifyContent: 'space-between',
                                                        alignItems: 'center',
                                                        transition: 'border-color 0.15s, background 0.15s',
                                                    }}
                                                    onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--primary-400)', e.currentTarget.style.background = 'var(--primary-50)')}
                                                    onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--gray-200)', e.currentTarget.style.background = '')}
                                                >
                                                    <div>
                                                        <div style={{ fontWeight: 600, fontSize: 14 }}>{client.name}</div>
                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 2 }}>
                                                            NRC: {client.nrc_number} · {client.phone}
                                                        </div>
                                                    </div>
                                                    <span className="badge badge-success" style={{ fontSize: 11 }}>KYC Verified</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <div className="modal-footer" style={{ justifyContent: 'flex-end' }}>
                                    <button className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                                </div>
                            </>
                        ) : (
                            <>
                                <div className="modal-body" style={{ maxHeight: '72vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
                                    {step2Loading ? (
                                        <div style={{ textAlign: 'center', padding: 48 }}>
                                            <div className="loading-spinner" style={{ width: 32, height: 32, margin: '0 auto 12px' }}></div>
                                            <div style={{ color: 'var(--gray-400)', fontSize: 13 }}>Loading KYC documents and products…</div>
                                        </div>
                                    ) : (
                                        <>
                                            {/* Client Profile Summary */}
                                            <div style={{ background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: 8, padding: 16 }}>
                                                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Client Profile</div>
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, fontSize: 13 }}>
                                                    <div>
                                                        <div style={{ color: 'var(--gray-400)', fontSize: 11 }}>Full Name</div>
                                                        <div style={{ fontWeight: 600 }}>{selectedClient.name}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ color: 'var(--gray-400)', fontSize: 11 }}>NRC Number</div>
                                                        <div style={{ fontWeight: 600, color: 'var(--primary-600)' }}>{selectedClient.nrc_number}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ color: 'var(--gray-400)', fontSize: 11 }}>Phone</div>
                                                        <div>{selectedClient.phone}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ color: 'var(--gray-400)', fontSize: 11 }}>Monthly Income</div>
                                                        <div style={{ fontWeight: 600 }}>ZMW {Number(selectedClient.monthly_income || 0).toLocaleString()}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ color: 'var(--gray-400)', fontSize: 11 }}>Employment</div>
                                                        <div>{selectedClient.employment_status?.replace('_', ' ')}</div>
                                                    </div>
                                                    <div>
                                                        <div style={{ color: 'var(--gray-400)', fontSize: 11 }}>Employer</div>
                                                        <div>{selectedClient.employer_name || '—'}</div>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* KYC Documents */}
                                            <div>
                                                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                                                    KYC Submission — Verified Documents
                                                </div>
                                                {!kycSubmission ? (
                                                    <div style={{ color: 'var(--gray-400)', fontSize: 13, padding: '12px 0' }}>No approved KYC submission found for this client.</div>
                                                ) : (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                                        {/* Group by section */}
                                                        {kycSubmission.field_values?.map((fv: any) => (
                                                            <div key={fv.id} style={{
                                                                display: 'flex',
                                                                justifyContent: 'space-between',
                                                                alignItems: 'center',
                                                                padding: '8px 12px',
                                                                background: fv.field_type === 'FILE' ? 'var(--primary-50)' : 'var(--gray-50)',
                                                                border: `1px solid ${fv.field_type === 'FILE' ? 'var(--primary-100)' : 'var(--gray-200)'}`,
                                                                borderRadius: 6,
                                                                fontSize: 13,
                                                            }}>
                                                                <span style={{ color: 'var(--gray-500)', minWidth: 180 }}>{fv.field_label}</span>
                                                                {fv.field_type === 'FILE' ? (
                                                                    <a
                                                                        href={fv.value_file}
                                                                        target="_blank"
                                                                        rel="noreferrer"
                                                                        style={{ color: 'var(--primary-600)', fontWeight: 600, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
                                                                    >
                                                                        📄 View Document
                                                                    </a>
                                                                ) : (
                                                                    <span style={{ fontWeight: 600, color: 'var(--gray-900)', textAlign: 'right' }}>{fv.value_text || '—'}</span>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Loan Product Eligibility */}
                                            <div>
                                                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                                                    Product Eligibility {amount ? `— ZMW ${Number(amount).toLocaleString()} cap` : '— Enter cap amount to filter'}
                                                </div>
                                                <div style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 10 }}>
                                                    Click a qualifying product to select it for this client.
                                                    {selectedProduct && <span style={{ color: 'var(--primary-600)', fontWeight: 600 }}> Selected: {selectedProduct.name}</span>}
                                                </div>
                                                {products.length === 0 ? (
                                                    <div style={{ color: 'var(--gray-400)', fontSize: 13 }}>No active loan products found.</div>
                                                ) : (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                                        {products.map(p => {
                                                            const qualifies = !amount || Number(amount) >= Number(p.min_amount);
                                                            const isSelected = selectedProduct?.id === p.id;
                                                            return (
                                                                <div
                                                                    key={p.id}
                                                                    onClick={() => qualifies && handleProductSelect(p)}
                                                                    style={{
                                                                        padding: '10px 14px',
                                                                        border: `2px solid ${isSelected ? 'var(--primary-500)' : qualifies ? 'var(--success)' : 'var(--gray-200)'}`,
                                                                        borderRadius: 8,
                                                                        background: isSelected ? 'var(--primary-50)' : qualifies ? '#F0FDF4' : 'var(--gray-50)',
                                                                        display: 'flex',
                                                                        justifyContent: 'space-between',
                                                                        alignItems: 'center',
                                                                        fontSize: 13,
                                                                        opacity: qualifies ? 1 : 0.45,
                                                                        cursor: qualifies ? 'pointer' : 'default',
                                                                        transition: 'border-color 0.15s, background 0.15s',
                                                                    }}
                                                                >
                                                                    <div>
                                                                        <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                                                                            {isSelected && <span style={{ color: 'var(--primary-600)' }}>✓</span>}
                                                                            {p.name}
                                                                        </div>
                                                                        <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 2 }}>
                                                                            ZMW {Number(p.min_amount).toLocaleString()} – {Number(p.max_amount).toLocaleString()} · {p.min_term}–{p.max_term} months · {p.interest_rate}% rate
                                                                        </div>
                                                                    </div>
                                                                    <span className={`badge ${isSelected ? 'badge-info' : qualifies ? 'badge-success' : 'badge-gray'}`} style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
                                                                        {isSelected ? 'Selected' : qualifies ? '✓ Qualifies' : '✗ Below minimum'}
                                                                    </span>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Qualification Decision */}
                                            <div style={{ borderTop: '2px solid var(--gray-100)', paddingTop: 20 }}>
                                                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 14 }}>
                                                    Qualification Decision
                                                </div>
                                                <div className="form-group">
                                                    <label className="form-label">Approved Loan Cap (ZMW) <span style={{ color: 'var(--error)' }}>*</span></label>
                                                    <input
                                                        className="form-control"
                                                        type="number"
                                                        min="0"
                                                        placeholder="e.g. 25000"
                                                        value={amount}
                                                        onChange={e => setAmount(e.target.value)}
                                                    />
                                                    <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 4 }}>
                                                        Maximum loan amount this client qualifies for. Product eligibility above updates as you type.
                                                    </div>
                                                </div>
                                                <div className="form-group">
                                                    <label className="form-label">Qualification Reason <span style={{ color: 'var(--error)' }}>*</span></label>
                                                    <textarea
                                                        className="form-control"
                                                        rows={3}
                                                        placeholder="e.g. Based on verified payslip showing ZMW 15,000 monthly income and clean NRC documents, client qualifies for ZMW 25,000..."
                                                        value={reason}
                                                        onChange={e => setReason(e.target.value)}
                                                    />
                                                    <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 4 }}>
                                                        This justification will be saved in the audit log.
                                                    </div>
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                                <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
                                    <button className="btn btn-secondary" onClick={() => setStep(1)}>← Back</button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={handleSave}
                                        disabled={saving || step2Loading || !amount || !reason.trim()}
                                    >
                                        {saving ? <span className="loading-spinner"></span> : null}
                                        Add to Qualified Base
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
