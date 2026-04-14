import { useState } from 'react';
import { authAPI } from '../services/api';
import { Eye, EyeOff, UserPlus, ArrowLeft } from 'lucide-react';

interface RegisterPageProps {
    onRegister: (user: any, access: string, refresh: string) => void;
    onBack: () => void;
}

export default function RegisterPage({ onRegister, onBack }: RegisterPageProps) {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        nrc_number: '',
        date_of_birth: '',
        gender: '',
        address: '',
        monthly_income: '',
        employment_status: 'EMPLOYED',
        employer_name: '',
        job_title: '',
        next_of_kin_name: '',
        next_of_kin_phone: '',
        next_of_kin_relation: '',
        password: '',
        confirm_password: ''
    });

    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (formData.password !== formData.confirm_password) {
            setError("Passwords do not match");
            return;
        }

        setLoading(true);
        try {
            const payload = {
                first_name: formData.first_name,
                last_name: formData.last_name,
                email: formData.email,
                phone: formData.phone,
                nrc_number: formData.nrc_number,
                date_of_birth: formData.date_of_birth,
                gender: formData.gender,
                address: formData.address,
                monthly_income: formData.monthly_income ? parseFloat(formData.monthly_income) : null,
                employment_status: formData.employment_status,
                employer_name: formData.employer_name,
                job_title: formData.job_title,
                next_of_kin_name: formData.next_of_kin_name,
                next_of_kin_phone: formData.next_of_kin_phone,
                next_of_kin_relation: formData.next_of_kin_relation,
                password: formData.password
            };
            const res = await authAPI.register(payload);
            onRegister(res.data.user, res.data.access, res.data.refresh);
        } catch (err: any) {
            const data = err.response?.data;
            let errorMsg = 'Registration failed. Please try again.';

            if (data) {
                if (data.error) errorMsg = data.error;
                else if (data.detail) errorMsg = data.detail;
                else if (data.non_field_errors?.length) errorMsg = data.non_field_errors[0];
                else if (typeof data === 'object') {
                    const firstKey = Object.keys(data)[0];
                    if (firstKey && Array.isArray(data[firstKey]) && data[firstKey].length) {
                        errorMsg = data[firstKey][0];
                    }
                }
            }

            setError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page" style={{ paddingBottom: '20px' }}>
            <div className="login-header" style={{ padding: '20px', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '15px' }}>
                <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
                    <ArrowLeft size={24} />
                </button>
                <div>
                    <h1 className="login-title" style={{ fontSize: '24px', margin: 0 }}>Create Account</h1>
                    <p className="login-subtitle" style={{ margin: 0, opacity: 0.8 }}>Join IntZam Loans today</p>
                </div>
            </div>

            <div className="login-form-container" style={{ marginTop: '10px', maxHeight: '70vh', overflowY: 'auto', paddingBottom: 80 }}>
                <h2 className="login-form-title">Your Details</h2>

                {error && (
                    <div className="alert alert-error" style={{ marginBottom: 20 }}>
                        <span>⚠️</span>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Full Name *</label>
                        <input
                            name="first_name"
                            type="text"
                            className="form-control"
                            placeholder="Enter your full name"
                            value={`${formData.first_name} ${formData.last_name}`.trim()}
                            onChange={(e) => {
                                const names = e.target.value.split(' ');
                                setFormData({ 
                                    ...formData, 
                                    first_name: names[0] || '',
                                    last_name: names.slice(1).join(' ') || ''
                                });
                            }}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Email *</label>
                        <input
                            name="email"
                            type="email"
                            className="form-control"
                            placeholder="your.email@example.com"
                            value={formData.email}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Phone *</label>
                        <input
                            name="phone"
                            type="tel"
                            className="form-control"
                            placeholder="e.g. +260970000000"
                            value={formData.phone}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">NRC Number</label>
                        <input
                            name="nrc_number"
                            type="text"
                            className="form-control"
                            placeholder="e.g. 123456/10/1"
                            value={formData.nrc_number}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Date of Birth</label>
                        <input
                            name="date_of_birth"
                            type="date"
                            className="form-control"
                            value={formData.date_of_birth}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Gender</label>
                        <select
                            name="gender"
                            className="form-control"
                            value={formData.gender}
                            onChange={handleChange}
                        >
                            <option value="">Select gender</option>
                            <option value="MALE">Male</option>
                            <option value="FEMALE">Female</option>
                            <option value="OTHER">Other</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Residential Address</label>
                        <textarea
                            name="address"
                            className="form-control"
                            placeholder="Your residential address"
                            value={formData.address}
                            onChange={handleChange}
                            rows={2}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Monthly Income (ZMW)</label>
                        <input
                            name="monthly_income"
                            type="number"
                            step="0.01"
                            className="form-control"
                            placeholder="0.00"
                            value={formData.monthly_income}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Employment Status</label>
                        <select
                            name="employment_status"
                            className="form-control"
                            value={formData.employment_status}
                            onChange={handleChange}
                        >
                            <option value="EMPLOYED">Employed</option>
                            <option value="SELF_EMPLOYED">Self Employed</option>
                            <option value="BUSINESS_OWNER">Business Owner</option>
                            <option value="UNEMPLOYED">Unemployed</option>
                            <option value="RETIRED">Retired</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Employer Name</label>
                        <input
                            name="employer_name"
                            type="text"
                            className="form-control"
                            placeholder="Company or employer name"
                            value={formData.employer_name}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Job Title</label>
                        <input
                            name="job_title"
                            type="text"
                            className="form-control"
                            placeholder="Your job title or position"
                            value={formData.job_title}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Next of Kin Name</label>
                        <input
                            name="next_of_kin_name"
                            type="text"
                            className="form-control"
                            placeholder="Emergency contact name"
                            value={formData.next_of_kin_name}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Next of Kin Phone</label>
                        <input
                            name="next_of_kin_phone"
                            type="tel"
                            className="form-control"
                            placeholder="Emergency contact phone"
                            value={formData.next_of_kin_phone}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Next of Kin Relationship</label>
                        <input
                            name="next_of_kin_relation"
                            type="text"
                            className="form-control"
                            placeholder="e.g. Spouse, Parent, Sibling"
                            value={formData.next_of_kin_relation}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Password *</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                name="password"
                                type={showPassword ? 'text' : 'password'}
                                className="form-control"
                                placeholder="Create a password"
                                value={formData.password}
                                onChange={handleChange}
                                required
                                minLength={8}
                                style={{ paddingRight: 48 }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute',
                                    right: 12,
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    color: 'var(--gray-400)',
                                    padding: 4,
                                }}
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Confirm Password *</label>
                        <input
                            name="confirm_password"
                            type={showPassword ? 'text' : 'password'}
                            className="form-control"
                            placeholder="Confirm your password"
                            value={formData.confirm_password}
                            onChange={handleChange}
                            required
                            minLength={8}
                        />
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-lg btn-block"
                        disabled={loading || !formData.first_name || !formData.email || !formData.phone || !formData.password}
                        style={{ marginTop: 8 }}
                    >
                        {loading ? (
                            <div className="loading-spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                        ) : (
                            <>
                                <UserPlus size={18} />
                                Create Account
                            </>
                        )}
                    </button>
                </form>

                <div className="login-footer">
                    <p>Already have an account? <span style={{ color: 'var(--primary-600)', cursor: 'pointer', fontWeight: 600 }} onClick={onBack}>Sign in</span></p>
                </div>
            </div>
        </div>
    );
}
