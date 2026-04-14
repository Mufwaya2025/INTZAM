import { useState, useEffect } from 'react';
import api from '../services/api';

export default function AuditLogsPage() {
    const [logs, setLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        loadLogs();
    }, []);

    const loadLogs = async () => {
        try {
            const res = await api.get('/audit-logs/');
            setLogs(res.data.results || res.data);
        } catch {
            // Error handling
        } finally {
            setLoading(false);
        }
    };

    const filtered = logs.filter(l =>
        l.action?.toLowerCase().includes(search.toLowerCase()) ||
        l.details?.toLowerCase().includes(search.toLowerCase()) ||
        l.performed_by_name?.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">System Audit Logs ({filtered.length})</h3>
                    <div className="flex gap-3">
                        <div className="search-bar">
                            <span className="search-icon">🔍</span>
                            <input
                                className="form-control"
                                placeholder="Search action, detail, user..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                style={{ paddingLeft: 36, width: 280 }}
                            />
                        </div>
                    </div>
                </div>
                <div className="table-container">
                    {loading ? (
                        <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Action</th>
                                    <th>Details</th>
                                    <th>Performed By</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} style={{ textAlign: 'center', padding: '40px 0' }}>No logs found</td>
                                    </tr>
                                ) : (
                                    filtered.map((log, i) => (
                                        <tr key={log.id || i}>
                                            <td style={{ whiteSpace: 'nowrap' }}>{new Date(log.created_at).toLocaleString()}</td>
                                            <td style={{ fontWeight: 600 }}>{log.action}</td>
                                            <td style={{ fontSize: '14px', color: 'var(--gray-600)' }}>{log.details}</td>
                                            <td>
                                                <span className="badge badge-gray">{log.performed_by_name || 'System'}</span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
}
