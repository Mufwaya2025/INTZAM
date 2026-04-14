import { useState, useEffect } from 'react';
import { kycAPI } from '../services/api';

const EMPTY_FIELD = { name: '', label: '', field_type: 'TEXT', required: true, order: 0, section: 0, options: [] as string[] };

export default function KYCBuilderPage() {
    const [sections, setSections] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [showSectionModal, setShowSectionModal] = useState(false);
    const [showFieldModal, setShowFieldModal] = useState(false);
    const [activeSectionId, setActiveSectionId] = useState<number | null>(null);
    const [editingField, setEditingField] = useState<any | null>(null);

    const [sectionForm, setSectionForm] = useState({ name: '', description: '', order: 0, is_active: true });
    const [fieldForm, setFieldForm] = useState({ ...EMPTY_FIELD });

    const getErrorMessage = (err: any, fallback: string) => {
        const data = err?.response?.data;
        if (data?.error) return data.error;
        if (data?.detail) return data.detail;
        if (data?.non_field_errors?.length) return data.non_field_errors[0];
        return fallback;
    };

    const loadData = () => {
        setLoading(true);
        kycAPI.sections().then(res => setSections(res.data.results || res.data)).finally(() => setLoading(false));
    };

    useEffect(() => { loadData(); }, []);

    const openAddField = (sectionId: number) => {
        setEditingField(null);
        setActiveSectionId(sectionId);
        setFieldForm({ ...EMPTY_FIELD });
        setShowFieldModal(true);
    };

    const openEditField = (field: any, sectionId: number) => {
        setEditingField(field);
        setActiveSectionId(sectionId);
        setFieldForm({
            name: field.name || '',
            label: field.label || '',
            field_type: field.field_type || 'TEXT',
            required: field.required ?? true,
            order: field.order ?? 0,
            section: sectionId,
            options: field.options || [],
        });
        setShowFieldModal(true);
    };

    const closeFieldModal = () => {
        setShowFieldModal(false);
        setEditingField(null);
        setFieldForm({ ...EMPTY_FIELD });
    };

    const handleSaveSection = async () => {
        try {
            await kycAPI.createSection(sectionForm);
            setShowSectionModal(false);
            setSectionForm({ name: '', description: '', order: 0, is_active: true });
            loadData();
        } catch (err) {
            alert('Failed to save section');
        }
    };

    const handleSaveField = async () => {
        try {
            if (editingField) {
                await kycAPI.updateField(editingField.id, { ...fieldForm, section: activeSectionId });
            } else {
                await kycAPI.createField({ ...fieldForm, section: activeSectionId });
            }
            closeFieldModal();
            loadData();
        } catch (err) {
            alert(editingField ? 'Failed to update field' : 'Failed to save field');
        }
    };

    const handleDeleteSection = async (id: number) => {
        if (!confirm('Are you sure you want to delete this section? All fields in this section and any submitted responses tied to them will be deleted.')) return;
        try {
            await kycAPI.deleteSection(id);
            loadData();
        } catch (err: any) {
            alert(getErrorMessage(err, 'Failed to delete section'));
        }
    };

    const handleDeleteField = async (id: number) => {
        if (!confirm('Are you sure you want to delete this field? Any submitted responses for this field will also be deleted.')) return;
        try {
            await kycAPI.deleteField(id);
            loadData();
        } catch (err: any) {
            alert(getErrorMessage(err, 'Failed to delete field'));
        }
    };

    const activeSectionName = sections.find(s => s.id === activeSectionId)?.name || '';

    return (
        <div>
            <div className="flex justify-between items-center" style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 24, fontWeight: 700 }}>KYC Form Builder</h1>
                <button className="btn btn-primary" onClick={() => setShowSectionModal(true)}>+ Add Section</button>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>Loading sections...</div>
            ) : sections.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-state-icon">📝</div>
                    <h3>No KYC Sections found</h3>
                    <p>Start by adding your first section for KYC Collection.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                    {sections.sort((a, b) => a.order - b.order).map(section => (
                        <div key={section.id} className="card">
                            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <div>
                                    <h3 style={{ margin: 0 }}>{section.name} <span className={`badge ${section.is_active ? 'badge-success' : 'badge-error'}`}>{section.is_active ? 'Active' : 'Inactive'}</span></h3>
                                    {section.description && <p style={{ margin: '4px 0 0 0', fontSize: 13, color: 'var(--gray-500)' }}>{section.description}</p>}
                                </div>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    <button className="btn btn-secondary btn-sm" onClick={() => openAddField(section.id)}>+ Add Field</button>
                                    <button className="btn btn-danger btn-sm" onClick={() => handleDeleteSection(section.id)}>Delete</button>
                                </div>
                            </div>
                            <div className="card-table">
                                <table className="table">
                                    <thead>
                                        <tr>
                                            <th>Label</th>
                                            <th>Machine Name</th>
                                            <th>Type</th>
                                            <th>Required</th>
                                            <th>Order</th>
                                            <th className="text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {section.fields?.sort((a: any, b: any) => a.order - b.order).map((field: any) => (
                                            <tr key={field.id}>
                                                <td><strong>{field.label}</strong></td>
                                                <td><code>{field.name}</code></td>
                                                <td>
                                                    <span className="badge badge-gray">{field.field_type}</span>
                                                    {field.field_type === 'SELECT' && field.options?.length > 0 && (
                                                        <div style={{ fontSize: 12, marginTop: 4, color: 'var(--gray-500)' }}>
                                                            Options: {field.options.join(', ')}
                                                        </div>
                                                    )}
                                                </td>
                                                <td><span className={`badge ${field.required ? 'badge-primary' : 'badge-gray'}`}>{field.required ? 'Yes' : 'No'}</span></td>
                                                <td>{field.order}</td>
                                                <td className="text-right">
                                                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                                                        <button className="btn btn-sm btn-secondary" onClick={() => openEditField(field, section.id)}>Edit</button>
                                                        <button className="btn btn-sm btn-danger" onClick={() => handleDeleteField(field.id)}>Delete</button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                        {(!section.fields || section.fields.length === 0) && (
                                            <tr>
                                                <td colSpan={6} className="text-center" style={{ padding: '24px 0', color: 'var(--gray-400)' }}>
                                                    No fields added yet.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Section Modal */}
            {showSectionModal && (
                <div className="modal-backdrop">
                    <div className="modal-content animate-in">
                        <div className="modal-header">
                            <h2 className="modal-title">Add KYC Section</h2>
                            <button className="modal-close" onClick={() => setShowSectionModal(false)}>×</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label className="form-label">Section Name</label>
                                <input className="form-control" value={sectionForm.name} onChange={e => setSectionForm({ ...sectionForm, name: e.target.value })} placeholder="e.g. Next of Kin" />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Description</label>
                                <textarea className="form-control" value={sectionForm.description} onChange={e => setSectionForm({ ...sectionForm, description: e.target.value })} />
                            </div>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label className="form-label">Display Order</label>
                                    <input type="number" className="form-control" value={sectionForm.order} onChange={e => setSectionForm({ ...sectionForm, order: Number(e.target.value) })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Is Active?</label>
                                    <select className="form-control" value={sectionForm.is_active ? 'true' : 'false'} onChange={e => setSectionForm({ ...sectionForm, is_active: e.target.value === 'true' })}>
                                        <option value="true">Yes</option>
                                        <option value="false">No</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowSectionModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleSaveSection}>Save Section</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Add / Edit Field Modal */}
            {showFieldModal && (
                <div className="modal-backdrop">
                    <div className="modal-content animate-in">
                        <div className="modal-header">
                            <h2 className="modal-title">
                                {editingField ? `Edit Field — ${editingField.label}` : `Add Field to "${activeSectionName}"`}
                            </h2>
                            <button className="modal-close" onClick={closeFieldModal}>×</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-grid">
                                <div className="form-group">
                                    <label className="form-label">Label (Display Name)</label>
                                    <input className="form-control" value={fieldForm.label} onChange={e => setFieldForm({ ...fieldForm, label: e.target.value })} placeholder="e.g. ID Front Image" />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Machine Name (no spaces)</label>
                                    <input className="form-control" value={fieldForm.name} onChange={e => setFieldForm({ ...fieldForm, name: e.target.value })} placeholder="e.g. id_front" />
                                </div>
                            </div>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label className="form-label">Field Type</label>
                                    <select className="form-control" value={fieldForm.field_type} onChange={e => setFieldForm({ ...fieldForm, field_type: e.target.value })}>
                                        <option value="TEXT">Short Text</option>
                                        <option value="LONG_TEXT">Long Text</option>
                                        <option value="NUMBER">Number</option>
                                        <option value="DATE">Date</option>
                                        <option value="SELECT">Dropdown Select</option>
                                        <option value="FILE">File Upload</option>
                                        <option value="BOOLEAN">Yes/No</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Display Order</label>
                                    <input type="number" className="form-control" value={fieldForm.order} onChange={e => setFieldForm({ ...fieldForm, order: Number(e.target.value) })} />
                                </div>
                            </div>
                            {fieldForm.field_type === 'SELECT' && (
                                <div className="form-group">
                                    <label className="form-label">Options (comma-separated)</label>
                                    <input
                                        className="form-control"
                                        value={fieldForm.options.join(',')}
                                        onChange={e => setFieldForm({ ...fieldForm, options: e.target.value.split(',').map(o => o.trim()).filter(o => o) })}
                                        placeholder="e.g. Option A, Option B, Option C"
                                    />
                                    <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
                                        Required for Dropdown Select fields. Separate options with commas.
                                    </div>
                                </div>
                            )}
                            <div className="form-group">
                                <label className="form-label">Is Required?</label>
                                <select className="form-control" value={fieldForm.required ? 'true' : 'false'} onChange={e => setFieldForm({ ...fieldForm, required: e.target.value === 'true' })}>
                                    <option value="true">Yes</option>
                                    <option value="false">No</option>
                                </select>
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={closeFieldModal}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleSaveField}>
                                {editingField ? 'Update Field' : 'Save Field'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
