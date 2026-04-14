import { useState, useEffect } from 'react';
import { productsAPI } from '../services/api';

export default function ProductsPage() {
    const [products, setProducts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editProduct, setEditProduct] = useState<any>(null);
    const [form, setForm] = useState<any>(DEFAULT_FORM);

    useEffect(() => { loadProducts(); }, []);

    const loadProducts = async () => {
        try {
            const res = await productsAPI.list();
            setProducts(res.data.results || res.data);
        } catch {
            setProducts(MOCK_PRODUCTS);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            if (editProduct) {
                await productsAPI.update(editProduct.id, form);
            } else {
                await productsAPI.create(form);
            }
            setShowModal(false);
            loadProducts();
        } catch (e: any) {
            alert('Error saving product');
        }
    };

    const openEdit = (p: any) => {
        setEditProduct(p);
        setForm({ ...p });
        setShowModal(true);
    };

    const openNew = () => {
        setEditProduct(null);
        setForm(DEFAULT_FORM);
        setShowModal(true);
    };

    const updateRate = (field: string, value: number) => {
        const updated = { ...form, [field]: value };
        updated.interest_rate = (Number(updated.nominal_interest_rate) || 0) +
            (Number(updated.credit_facilitation_fee) || 0) +
            (Number(updated.processing_fee) || 0);
        setForm(updated);
    };

    return (
        <div>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Loan Products ({products.length})</h3>
                    <button className="btn btn-primary" onClick={openNew}>+ New Product</button>
                </div>
                <div className="table-container">
                    {loading ? (
                        <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Product Name</th>
                                    <th>Type</th>
                                    <th>Rate</th>
                                    <th>Amount Range</th>
                                    <th>Term Range</th>
                                    <th>Frequency</th>
                                    <th>Max Rollovers</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {products.map(p => (
                                    <tr key={p.id}>
                                        <td>
                                            <div style={{ fontWeight: 600 }}>{p.name}</div>
                                            <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{p.description?.slice(0, 50)}...</div>
                                        </td>
                                        <td><span className="badge badge-purple">{p.interest_type}</span></td>
                                        <td><strong>{p.interest_rate}%</strong></td>
                                        <td>ZMW {Number(p.min_amount).toLocaleString()} – ZMW {Number(p.max_amount).toLocaleString()}</td>
                                        <td>{p.min_term} – {p.max_term} months</td>
                                        <td><span className="badge badge-info">{p.repayment_frequency || 'MONTHLY'}</span></td>
                                        <td>{p.max_rollovers}</td>
                                        <td><span className={`badge ${p.is_active ? 'badge-success' : 'badge-error'}`}>{p.is_active ? 'Active' : 'Inactive'}</span></td>
                                        <td>
                                            <button className="btn btn-secondary btn-sm" onClick={() => openEdit(p)}>Edit</button>
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
                    <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="modal-title">{editProduct ? 'Edit Product' : 'New Loan Product'}</h3>
                            <button className="btn btn-secondary btn-icon" onClick={() => setShowModal(false)}>✕</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-grid">
                                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                                    <label className="form-label">Product Name *</label>
                                    <input className="form-control" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                                </div>
                                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                                    <label className="form-label">Description</label>
                                    <textarea className="form-control" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Interest Type</label>
                                    <select className="form-control" value={form.interest_type} onChange={e => setForm({ ...form, interest_type: e.target.value })}>
                                        <option value="FLAT">Flat Rate</option>
                                        <option value="REDUCING">Reducing Balance</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Repayment Frequency</label>
                                    <select className="form-control" value={form.repayment_frequency} onChange={e => setForm({ ...form, repayment_frequency: e.target.value })}>
                                        <option value="MONTHLY">Monthly</option>
                                        <option value="BIWEEKLY">Bi-Weekly (Every 2 Weeks)</option>
                                        <option value="WEEKLY">Weekly</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Total Rate: <strong>{form.interest_rate}%</strong></label>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                                        <div>
                                            <label style={{ fontSize: 11, color: 'var(--gray-500)' }}>Nominal %</label>
                                            <input className="form-control" type="number" value={form.nominal_interest_rate} onChange={e => updateRate('nominal_interest_rate', Number(e.target.value))} />
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 11, color: 'var(--gray-500)' }}>Facilitation %</label>
                                            <input className="form-control" type="number" value={form.credit_facilitation_fee} onChange={e => updateRate('credit_facilitation_fee', Number(e.target.value))} />
                                        </div>
                                        <div>
                                            <label style={{ fontSize: 11, color: 'var(--gray-500)' }}>Processing %</label>
                                            <input className="form-control" type="number" value={form.processing_fee} onChange={e => updateRate('processing_fee', Number(e.target.value))} />
                                        </div>
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Min Amount (ZMW)</label>
                                    <input className="form-control" type="number" value={form.min_amount} onChange={e => setForm({ ...form, min_amount: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Max Amount (ZMW)</label>
                                    <input className="form-control" type="number" value={form.max_amount} onChange={e => setForm({ ...form, max_amount: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Min Term (months)</label>
                                    <input className="form-control" type="number" value={form.min_term} onChange={e => setForm({ ...form, min_term: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Max Term (months)</label>
                                    <input className="form-control" type="number" value={form.max_term} onChange={e => setForm({ ...form, max_term: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Penalty Rate (%)</label>
                                    <input className="form-control" type="number" value={form.penalty_rate} onChange={e => setForm({ ...form, penalty_rate: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Grace Period (days)</label>
                                    <input className="form-control" type="number" value={form.grace_period_days} onChange={e => setForm({ ...form, grace_period_days: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Max Rollovers</label>
                                    <input className="form-control" type="number" value={form.max_rollovers} onChange={e => setForm({ ...form, max_rollovers: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Rollover Rate (%)</label>
                                    <input className="form-control" type="number" value={form.rollover_interest_rate} onChange={e => setForm({ ...form, rollover_interest_rate: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Min Principal Paid for Rollover (%)</label>
                                    <input className="form-control" type="number" value={form.rollover_min_principal_paid_percent} onChange={e => setForm({ ...form, rollover_min_principal_paid_percent: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Rollover Extension (days)</label>
                                    <input className="form-control" type="number" value={form.rollover_extension_days} onChange={e => setForm({ ...form, rollover_extension_days: e.target.value })} />
                                </div>
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleSave}>Save Product</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

const DEFAULT_FORM = {
    name: '', description: '', interest_type: 'FLAT', repayment_frequency: 'MONTHLY',
    interest_rate: 25, nominal_interest_rate: 18, credit_facilitation_fee: 5, processing_fee: 2,
    min_amount: 500, max_amount: 50000, min_term: 1, max_term: 24,
    penalty_rate: 5, grace_period_days: 3,
    rollover_interest_rate: 4, max_rollovers: 2, rollover_min_principal_paid_percent: 30, rollover_extension_days: 14,
    required_documents: [], is_active: true,
};

const MOCK_PRODUCTS = [
    { id: 1, name: 'IntZam Personal', description: 'Unsecured personal loan for salaried individuals', interest_type: 'FLAT', interest_rate: 25, min_amount: 500, max_amount: 50000, min_term: 1, max_term: 24, max_rollovers: 2, is_active: true },
    { id: 2, name: 'SME Growth', description: 'Working capital for small businesses', interest_type: 'REDUCING', interest_rate: 30, min_amount: 2000, max_amount: 100000, min_term: 6, max_term: 36, max_rollovers: 3, is_active: true },
];
