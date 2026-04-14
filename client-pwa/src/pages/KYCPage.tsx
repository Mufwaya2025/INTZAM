import { useState, useEffect } from 'react';
import { kycAPI, clientsAPI } from '../services/api';
import { ArrowLeft, ArrowRight, Check, AlertCircle, FileText, Upload, Lock } from 'lucide-react';
import type { Page } from '../components/AppShell';

interface KYCPageProps {
    navigate: (page: Page) => void;
}

function getProfileValue(label: string, sectionName: string, profile: any): string {
    const l = label.toLowerCase();
    const s = sectionName.toLowerCase();
    const isKin = s.includes('kin') || s.includes('emergency');

    if (l.includes('full name') || l === 'name') {
        return isKin ? (profile.next_of_kin_name || '') : (profile.name || '');
    }
    if (l.includes('date of birth') || l.includes('dob')) return profile.date_of_birth || '';
    if (l.includes('nrc')) return profile.nrc_number || '';
    if ((l.includes('phone') || l.includes('mobile')) && !l.includes('employer')) {
        return isKin ? (profile.next_of_kin_phone || '') : (profile.phone || '');
    }
    if (l.includes('email')) return profile.email && !profile.email.includes('@example.com') ? profile.email : '';
    if (l.includes('address') && !isKin) return profile.address || '';
    if (l.includes('employment status')) return profile.employment_status || '';
    if (l.includes('employer')) return profile.employer_name || '';
    if (l.includes('job title') || l.includes('position')) return profile.job_title || '';
    if (l.includes('monthly income') || (l.includes('income') && !l.includes('proof'))) {
        return profile.monthly_income ? String(profile.monthly_income) : '';
    }
    if (l.includes('relationship') || l.includes('relation')) return profile.next_of_kin_relation || '';

    return '';
}

export default function KYCPage({ navigate }: KYCPageProps) {
    const [sections, setSections] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [existingSubmission, setExistingSubmission] = useState<any>(null);
    const [currentStep, setCurrentStep] = useState(0);

    const [formValues, setFormValues] = useState<Record<number, string>>({});
    const [fileValues, setFileValues] = useState<Record<number, File>>({});
    const [prefilledFields, setPrefilledFields] = useState<Set<number>>(new Set());
    const [unlockedFields, setUnlockedFields] = useState<Set<number>>(new Set());
    const [stepError, setStepError] = useState('');

    useEffect(() => {
        Promise.all([
            kycAPI.sections().catch(() => ({ data: [] })),
            kycAPI.submissions().catch(() => ({ data: [] })),
            clientsAPI.list().catch(() => ({ data: [] })),
        ]).then(([sectionsRes, submissionsRes, clientsRes]) => {
            const sectionsData = Array.isArray(sectionsRes.data?.results) ? sectionsRes.data.results : (Array.isArray(sectionsRes.data) ? sectionsRes.data : []);
            const activeSections = sectionsData.filter((s: any) => s.is_active).sort((a: any, b: any) => a.order - b.order);
            setSections(activeSections);

            const submissionsData = Array.isArray(submissionsRes.data?.results) ? submissionsRes.data.results : (Array.isArray(submissionsRes.data) ? submissionsRes.data : []);
            const realSubmission = submissionsData.find((s: any) => s.field_values?.length > 0);
            if (realSubmission) setExistingSubmission(realSubmission);

            const profile = Array.isArray(clientsRes.data) ? clientsRes.data[0] : clientsRes.data?.results?.[0];
            if (profile) {
                const initialValues: Record<number, string> = {};
                const prefilled = new Set<number>();
                for (const section of activeSections) {
                    for (const field of section.fields || []) {
                        if (field.field_type === 'FILE') continue;
                        const val = getProfileValue(field.label, section.name, profile);
                        if (val) {
                            initialValues[field.id] = val;
                            prefilled.add(field.id);
                        }
                    }
                }
                setFormValues(initialValues);
                setPrefilledFields(prefilled);
            }
        }).catch((err) => {
            setError(err.message || 'Failed to load KYC data.');
        }).finally(() => setLoading(false));
    }, []);

    const handleTextChange = (fieldId: number, val: string) => {
        setFormValues(prev => ({ ...prev, [fieldId]: val }));
    };

    const handleFileChange = (fieldId: number, e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFileValues(prev => ({ ...prev, [fieldId]: e.target.files![0] }));
        }
    };

    const validateStep = (section: any): boolean => {
        const fields = section.fields || [];
        for (const field of fields) {
            if (!field.required) continue;
            if (field.field_type === 'FILE') {
                if (!fileValues[field.id]) {
                    setStepError(`Please upload: ${field.label}`);
                    return false;
                }
            } else {
                if (!formValues[field.id]?.trim()) {
                    setStepError(`Please fill in: ${field.label}`);
                    return false;
                }
            }
        }
        setStepError('');
        return true;
    };

    const handleNext = () => {
        if (!validateStep(sections[currentStep])) return;
        setCurrentStep(s => s + 1);
        window.scrollTo(0, 0);
    };

    const handleBack = () => {
        setStepError('');
        setCurrentStep(s => s - 1);
        window.scrollTo(0, 0);
    };

    const handleSubmit = async () => {
        if (!validateStep(sections[currentStep])) return;
        setSubmitting(true);
        setError('');

        const formData = new FormData();
        Object.keys(formValues).forEach(key => {
            if (formValues[Number(key)] !== '') {
                formData.append(`field_${key}`, formValues[Number(key)]);
            }
        });
        Object.keys(fileValues).forEach(key => {
            formData.append(`field_${key}`, fileValues[Number(key)]);
        });

        try {
            await kycAPI.submit(formData);
            setSuccess(true);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Failed to submit. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    if (success) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '80vh', padding: 40, textAlign: 'center' }}>
                <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'var(--success-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 24 }}>
                    <Check size={36} color="var(--success)" />
                </div>
                <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--gray-900)', marginBottom: 8 }}>Submitted!</h2>
                <p style={{ fontSize: 14, color: 'var(--gray-500)', lineHeight: 1.6, marginBottom: 32, maxWidth: 300 }}>
                    Your KYC information has been sent for review. We will notify you once it's approved.
                </p>
                <button className="btn btn-primary" onClick={() => navigate({ name: 'dashboard' })}>Return Home</button>
            </div>
        );
    }

    if (loading) {
        return (
            <div>
                <div className="page-header">
                    <div className="page-header-back" onClick={() => navigate({ name: 'profile' })}><ArrowLeft size={20} /></div>
                    <span className="page-header-title">Document Verification</span>
                </div>
                <div style={{ textAlign: 'center', padding: 60 }}>
                    <div className="loading-spinner" style={{ width: 32, height: 32 }}></div>
                </div>
            </div>
        );
    }

    // Show status view for submitted/approved/pending submissions
    if (existingSubmission && existingSubmission.status !== 'REJECTED') {
        return (
            <div>
                <div className="page-header">
                    <div className="page-header-back" onClick={() => navigate({ name: 'profile' })}><ArrowLeft size={20} /></div>
                    <span className="page-header-title">Document Verification</span>
                </div>
                <div className="section animate-in">
                    <div className={`alert ${existingSubmission.status === 'APPROVED' ? 'alert-success' : 'alert-info'}`} style={{ marginBottom: 20 }}>
                        <AlertCircle size={16} />
                        <div>
                            {existingSubmission.status === 'APPROVED'
                                ? <span><strong>Verified!</strong> Your identity has been confirmed. You are eligible to apply for loans.</span>
                                : <span><strong>Under Review</strong> — submitted on {new Date(existingSubmission.created_at).toLocaleDateString()}. Our team is reviewing your documents.</span>
                            }
                        </div>
                    </div>
                    {existingSubmission.field_values?.length > 0 && (
                        <div className="card">
                            <div className="card-header" style={{ padding: '14px 20px' }}>
                                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Submitted Documents</h3>
                            </div>
                            <div className="card-body" style={{ padding: '0 0 8px' }}>
                                {existingSubmission.field_values.map((fv: any) => (
                                    <div key={fv.id} style={{ padding: '12px 20px', borderBottom: '1px solid var(--gray-50)', display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{ width: 36, height: 36, borderRadius: 10, background: fv.field_type === 'FILE' ? 'var(--primary-50)' : 'var(--gray-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                            <FileText size={16} color={fv.field_type === 'FILE' ? 'var(--primary-600)' : 'var(--gray-500)'} />
                                        </div>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 2 }}>{fv.field_label}</div>
                                            {fv.field_type === 'FILE'
                                                ? fv.value_file
                                                    ? <a href={fv.value_file} target="_blank" rel="noreferrer" style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary-600)' }}>View Document</a>
                                                    : <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>Not uploaded</span>
                                                : <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-900)' }}>{fv.value_text || '—'}</span>
                                            }
                                        </div>
                                        {existingSubmission.status === 'APPROVED' && <Check size={16} color="var(--success)" />}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    if (sections.length === 0) {
        return (
            <div>
                <div className="page-header">
                    <div className="page-header-back" onClick={() => navigate({ name: 'profile' })}><ArrowLeft size={20} /></div>
                    <span className="page-header-title">Document Verification</span>
                </div>
                <div className="empty-state">
                    <div className="empty-state-icon">📝</div>
                    <h3>No Forms Available</h3>
                    <p>Our team is currently preparing the KYC forms. Please try again later.</p>
                </div>
            </div>
        );
    }

    const section = sections[currentStep];
    const isLastStep = currentStep === sections.length - 1;
    const progress = ((currentStep + 1) / sections.length) * 100;
    const fields = section.fields?.sort((a: any, b: any) => a.order - b.order) || [];

    return (
        <div style={{ paddingBottom: 100 }}>
            {/* Header */}
            <div className="page-header">
                <div className="page-header-back" onClick={currentStep === 0 ? () => navigate({ name: 'profile' }) : handleBack}>
                    <ArrowLeft size={20} />
                </div>
                <span className="page-header-title">Document Verification</span>
                <span style={{ fontSize: 12, color: 'var(--gray-400)', fontWeight: 600 }}>
                    {currentStep + 1} / {sections.length}
                </span>
            </div>

            {/* Progress Bar */}
            <div style={{ height: 4, background: 'var(--gray-100)', margin: '0 0 4px' }}>
                <div style={{
                    height: '100%',
                    width: `${progress}%`,
                    background: 'linear-gradient(90deg, var(--primary-500), var(--primary-600))',
                    borderRadius: '0 4px 4px 0',
                    transition: 'width 0.4s ease',
                }} />
            </div>

            {/* Step Dots */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 6, padding: '12px 20px 4px' }}>
                {sections.map((_, i) => (
                    <div key={i} style={{
                        width: i === currentStep ? 20 : 7,
                        height: 7,
                        borderRadius: 4,
                        background: i < currentStep ? 'var(--success)' : i === currentStep ? 'var(--primary-600)' : 'var(--gray-200)',
                        transition: 'all 0.3s ease',
                    }} />
                ))}
            </div>

            <div className="section animate-in" key={currentStep}>
                {/* Rejection banner if re-submitting */}
                {existingSubmission?.status === 'REJECTED' && currentStep === 0 && (
                    <div className="alert alert-error" style={{ marginBottom: 20 }}>
                        <AlertCircle size={16} />
                        <div>
                            <strong>Previously Rejected</strong>
                            {existingSubmission.reviewer_notes && <div style={{ marginTop: 4 }}>Reason: {existingSubmission.reviewer_notes}</div>}
                            <div style={{ marginTop: 4, fontSize: 13 }}>Please re-submit with the correct documents.</div>
                        </div>
                    </div>
                )}

                {/* Section card */}
                <div className="card" style={{ marginBottom: 16 }}>
                    <div className="card-header" style={{ padding: '16px 20px', borderBottom: '1px solid var(--gray-100)' }}>
                        <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>{section.name}</h3>
                        {section.description && (
                            <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--gray-500)' }}>{section.description}</p>
                        )}
                    </div>
                    <div className="card-body" style={{ padding: 20 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            {fields.map((field: any) => {
                                const isPrefilled = prefilledFields.has(field.id);
                                const isUnlocked = unlockedFields.has(field.id);
                                const showReadOnly = isPrefilled && !isUnlocked && field.field_type !== 'FILE';

                                return (
                                    <div key={field.id}>
                                        <label className="form-label" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                                            <span>
                                                {field.label}
                                                {field.required && <span style={{ color: 'var(--error)', marginLeft: 2 }}>*</span>}
                                            </span>
                                            {isPrefilled && !isUnlocked && (
                                                <button
                                                    type="button"
                                                    onClick={() => setUnlockedFields(prev => new Set([...prev, field.id]))}
                                                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: 'var(--gray-400)', display: 'flex', alignItems: 'center', gap: 3, padding: 0 }}
                                                >
                                                    <Lock size={11} /> Edit
                                                </button>
                                            )}
                                        </label>

                                        {showReadOnly ? (
                                            <div style={{
                                                padding: '11px 14px',
                                                background: 'var(--gray-50)',
                                                border: '1.5px solid var(--gray-100)',
                                                borderRadius: 10,
                                                fontSize: 14,
                                                color: 'var(--gray-700)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 8,
                                            }}>
                                                <Check size={14} color="var(--success)" style={{ flexShrink: 0 }} />
                                                <span style={{ flex: 1 }}>{formValues[field.id]}</span>
                                                <span style={{ fontSize: 11, color: 'var(--gray-400)', fontWeight: 500, whiteSpace: 'nowrap' }}>From profile</span>
                                            </div>
                                        ) : (
                                            <>
                                                {field.field_type === 'TEXT' && (
                                                    <input className="form-control" value={formValues[field.id] || ''} onChange={e => handleTextChange(field.id, e.target.value)} />
                                                )}
                                                {field.field_type === 'LONG_TEXT' && (
                                                    <textarea className="form-control" rows={3} value={formValues[field.id] || ''} onChange={e => handleTextChange(field.id, e.target.value)} />
                                                )}
                                                {field.field_type === 'NUMBER' && (
                                                    <input type="number" className="form-control" value={formValues[field.id] || ''} onChange={e => handleTextChange(field.id, e.target.value)} />
                                                )}
                                                {field.field_type === 'DATE' && (
                                                    <input type="date" className="form-control" value={formValues[field.id] || ''} onChange={e => handleTextChange(field.id, e.target.value)} />
                                                )}
                                                {field.field_type === 'SELECT' && (
                                                    <select className="form-control" value={formValues[field.id] || ''} onChange={e => handleTextChange(field.id, e.target.value)}>
                                                        <option value="">Select option...</option>
                                                        {field.options?.map((opt: string, idx: number) => (
                                                            <option key={idx} value={opt}>{opt}</option>
                                                        ))}
                                                    </select>
                                                )}
                                                {field.field_type === 'BOOLEAN' && (
                                                    <select className="form-control" value={formValues[field.id] || ''} onChange={e => handleTextChange(field.id, e.target.value)}>
                                                        <option value="">Select option...</option>
                                                        <option value="Yes">Yes</option>
                                                        <option value="No">No</option>
                                                    </select>
                                                )}
                                                {field.field_type === 'FILE' && (
                                                    <label style={{
                                                        display: 'flex',
                                                        flexDirection: 'column',
                                                        alignItems: 'center',
                                                        gap: 8,
                                                        border: `2px dashed ${fileValues[field.id] ? 'var(--primary-400)' : 'var(--gray-200)'}`,
                                                        borderRadius: 12,
                                                        padding: '24px 16px',
                                                        background: fileValues[field.id] ? 'var(--primary-50)' : 'var(--gray-50)',
                                                        cursor: 'pointer',
                                                        transition: 'all 0.2s',
                                                    }}>
                                                        <div style={{
                                                            width: 48, height: 48, borderRadius: 12,
                                                            background: fileValues[field.id] ? 'var(--primary-100)' : 'white',
                                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                                                        }}>
                                                            {fileValues[field.id]
                                                                ? <Check size={22} color="var(--primary-600)" />
                                                                : <Upload size={22} color="var(--gray-400)" />
                                                            }
                                                        </div>
                                                        {fileValues[field.id] ? (
                                                            <div style={{ textAlign: 'center' }}>
                                                                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary-700)' }}>{fileValues[field.id].name}</div>
                                                                <div style={{ fontSize: 11, color: 'var(--primary-500)', marginTop: 2 }}>Tap to change</div>
                                                            </div>
                                                        ) : (
                                                            <div style={{ textAlign: 'center' }}>
                                                                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-700)' }}>Tap to upload</div>
                                                                <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 2 }}>PDF, JPG or PNG — max 5MB</div>
                                                            </div>
                                                        )}
                                                        <input
                                                            type="file"
                                                            accept=".pdf,.jpg,.jpeg,.png"
                                                            onChange={e => handleFileChange(field.id, e)}
                                                            style={{ display: 'none' }}
                                                        />
                                                    </label>
                                                )}
                                            </>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Step validation error */}
                {stepError && (
                    <div className="alert alert-error" style={{ marginBottom: 16 }}>
                        <AlertCircle size={14} />
                        <span>{stepError}</span>
                    </div>
                )}

                {/* Submission error */}
                {error && (
                    <div className="alert alert-error" style={{ marginBottom: 16 }}>
                        <AlertCircle size={14} />
                        <span>{error}</span>
                    </div>
                )}

                {/* Navigation buttons */}
                <div style={{ display: 'flex', gap: 10 }}>
                    {currentStep > 0 && (
                        <button className="btn btn-secondary" onClick={handleBack} style={{ flex: 1 }}>
                            <ArrowLeft size={16} /> Back
                        </button>
                    )}
                    {isLastStep ? (
                        <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting} style={{ flex: 1 }}>
                            {submitting
                                ? <div className="loading-spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
                                : <><Check size={16} /> Submit</>
                            }
                        </button>
                    ) : (
                        <button className="btn btn-primary" onClick={handleNext} style={{ flex: 1 }}>
                            Next <ArrowRight size={16} />
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
