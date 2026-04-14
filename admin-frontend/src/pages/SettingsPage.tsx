import { useState, useEffect } from 'react';
import { settingsAPI } from '../services/api';

interface SmtpConfig {
    smtp_host: string;
    smtp_port: string;
    smtp_username: string;
    smtp_password: string;
    smtp_use_tls: string;
    smtp_use_ssl: string;
    smtp_from_email: string;
}

const DEFAULT_CONFIG: SmtpConfig = {
    smtp_host: '',
    smtp_port: '587',
    smtp_username: '',
    smtp_password: '',
    smtp_use_tls: 'true',
    smtp_use_ssl: 'false',
    smtp_from_email: '',
};

export default function SettingsPage() {
    const [config, setConfig] = useState<SmtpConfig>(DEFAULT_CONFIG);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [saveMsg, setSaveMsg] = useState('');
    const [saveError, setSaveError] = useState('');
    const [testMsg, setTestMsg] = useState('');
    const [testError, setTestError] = useState('');

    useEffect(() => {
        settingsAPI.getSmtp()
            .then(res => {
                setConfig({
                    smtp_host: res.data.smtp_host || '',
                    smtp_port: res.data.smtp_port || '587',
                    smtp_username: res.data.smtp_username || '',
                    smtp_password: res.data.smtp_password || '',
                    smtp_use_tls: res.data.smtp_use_tls !== undefined ? String(res.data.smtp_use_tls) : 'true',
                    smtp_use_ssl: res.data.smtp_use_ssl !== undefined ? String(res.data.smtp_use_ssl) : 'false',
                    smtp_from_email: res.data.smtp_from_email || '',
                });
            })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const handleChange = (key: keyof SmtpConfig, value: string) => {
        setConfig(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setSaveMsg('');
        setSaveError('');
        try {
            await settingsAPI.saveSmtp(config);
            setSaveMsg('Configuration saved successfully.');
        } catch (err: any) {
            setSaveError(err.response?.data?.error || 'Failed to save configuration.');
        } finally {
            setSaving(false);
        }
    };

    const handleTestEmail = async () => {
        setTesting(true);
        setTestMsg('');
        setTestError('');
        try {
            const res = await settingsAPI.testEmail('');
            setTestMsg(res.data.message || 'Test email sent.');
        } catch (err: any) {
            setTestError(err.response?.data?.error || 'Failed to send test email.');
        } finally {
            setTesting(false);
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
                <div className="loading-spinner" style={{ width: 32, height: 32 }}></div>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 640 }}>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">SMTP Email Configuration</h3>
                    <p style={{ color: 'var(--gray-500)', fontSize: 14, marginTop: 4 }}>
                        Configure the outgoing email server used for password resets and system notifications.
                    </p>
                </div>
                <div className="card-body">
                    {saveMsg && (
                        <div className="alert alert-success" style={{ marginBottom: 16 }}>
                            <span>✓</span> {saveMsg}
                        </div>
                    )}
                    {saveError && (
                        <div className="alert alert-error" style={{ marginBottom: 16 }}>
                            <span>⚠️</span> {saveError}
                        </div>
                    )}

                    <form onSubmit={handleSave}>
                        <div className="form-group">
                            <label className="form-label">SMTP Host</label>
                            <input
                                type="text"
                                className="form-control"
                                placeholder="smtp.gmail.com"
                                value={config.smtp_host}
                                onChange={e => handleChange('smtp_host', e.target.value)}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">SMTP Port</label>
                            <input
                                type="number"
                                className="form-control"
                                placeholder="587"
                                value={config.smtp_port}
                                onChange={e => handleChange('smtp_port', e.target.value)}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Username</label>
                            <input
                                type="text"
                                className="form-control"
                                placeholder="your-email@gmail.com"
                                value={config.smtp_username}
                                onChange={e => handleChange('smtp_username', e.target.value)}
                                autoComplete="off"
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Password / App Password</label>
                            <input
                                type="password"
                                className="form-control"
                                placeholder="Leave blank to keep existing password"
                                value={config.smtp_password}
                                onChange={e => handleChange('smtp_password', e.target.value)}
                                autoComplete="new-password"
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">From Email</label>
                            <input
                                type="email"
                                className="form-control"
                                placeholder="noreply@intzam.com"
                                value={config.smtp_from_email}
                                onChange={e => handleChange('smtp_from_email', e.target.value)}
                            />
                        </div>

                        <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={config.smtp_use_tls === 'true'}
                                    onChange={e => handleChange('smtp_use_tls', e.target.checked ? 'true' : 'false')}
                                />
                                <span className="form-label" style={{ margin: 0 }}>Use TLS</span>
                            </label>

                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={config.smtp_use_ssl === 'true'}
                                    onChange={e => handleChange('smtp_use_ssl', e.target.checked ? 'true' : 'false')}
                                />
                                <span className="form-label" style={{ margin: 0 }}>Use SSL</span>
                            </label>
                        </div>

                        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={saving}
                            >
                                {saving ? (
                                    <div className="loading-spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></div>
                                ) : 'Save Configuration'}
                            </button>

                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={handleTestEmail}
                                disabled={testing}
                            >
                                {testing ? (
                                    <div className="loading-spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></div>
                                ) : 'Send Test Email'}
                            </button>
                        </div>
                    </form>

                    {testMsg && (
                        <div className="alert alert-success" style={{ marginTop: 16 }}>
                            <span>✓</span> {testMsg}
                        </div>
                    )}
                    {testError && (
                        <div className="alert alert-error" style={{ marginTop: 16 }}>
                            <span>⚠️</span> {testError}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
