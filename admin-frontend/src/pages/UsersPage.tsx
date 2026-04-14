import { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { PERMISSION_GROUPS, ROLE_DEFAULTS } from '../permissions';

export default function UsersPage() {
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    // User create/edit modal
    const [showModal, setShowModal] = useState(false);
    const [editUser, setEditUser] = useState<any>(null);
    const [form, setForm] = useState<any>({ username: '', email: '', first_name: '', last_name: '', role: 'CLIENT', password: '', phone: '' });

    // Reset password modal
    const [resetUser, setResetUser] = useState<any>(null);
    const [resetPassword, setResetPassword] = useState('');
    const [resetLoading, setResetLoading] = useState(false);

    // Permissions modal
    const [permsUser, setPermsUser] = useState<any>(null);
    const [permsSelected, setPermsSelected] = useState<string[]>([]);
    const [permsLoading, setPermsLoading] = useState(false);

    useEffect(() => { loadUsers(); }, []);

    const loadUsers = async () => {
        try {
            const res = await authAPI.getUsers();
            setUsers(res.data.results || res.data);
        } catch {
            setUsers(MOCK_USERS);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            const data = { ...form };
            if (!data.password) delete data.password;
            if (editUser) {
                await authAPI.updateUser(editUser.id, data);
            } else {
                await authAPI.createUser(data);
            }
            setShowModal(false);
            loadUsers();
        } catch (e: any) {
            alert(e.response?.data?.username?.[0] || e.response?.data?.email?.[0] || 'Error saving user');
        }
    };

    const openEdit = (user: any) => {
        setEditUser(user);
        setForm({ ...user, password: '' });
        setShowModal(true);
    };

    const openNew = () => {
        setEditUser(null);
        setForm({ username: '', email: '', first_name: '', last_name: '', role: 'PORTFOLIO_MANAGER', password: '', phone: '' });
        setShowModal(true);
    };

    // --- Reset password ---
    const openReset = (user: any) => {
        setResetUser(user);
        setResetPassword('');
    };

    const handleResetPassword = async () => {
        if (!resetPassword || resetPassword.length < 8) return;
        setResetLoading(true);
        try {
            await authAPI.updateUser(resetUser.id, { password: resetPassword });
            setResetUser(null);
        } catch {
            alert('Failed to reset password');
        } finally {
            setResetLoading(false);
        }
    };

    // --- Permissions modal ---
    const openPerms = (user: any) => {
        setPermsUser(user);
        // If custom permissions are set, show those; otherwise pre-fill with role defaults
        setPermsSelected(
            user.custom_permissions?.length > 0
                ? [...user.custom_permissions]
                : [...(ROLE_DEFAULTS[user.role] ?? [])]
        );
    };

    const togglePerm = (key: string) => {
        setPermsSelected(prev =>
            prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
        );
    };

    const toggleGroup = (keys: string[]) => {
        const allOn = keys.every(k => permsSelected.includes(k));
        if (allOn) {
            setPermsSelected(prev => prev.filter(k => !keys.includes(k)));
        } else {
            setPermsSelected(prev => [...new Set([...prev, ...keys])]);
        }
    };

    const savePerms = async () => {
        setPermsLoading(true);
        try {
            await authAPI.updateUser(permsUser.id, { custom_permissions: permsSelected });
            setPermsUser(null);
            loadUsers();
        } catch {
            alert('Failed to save permissions');
        } finally {
            setPermsLoading(false);
        }
    };

    const resetToRoleDefaults = async () => {
        setPermsLoading(true);
        try {
            await authAPI.updateUser(permsUser.id, { custom_permissions: [] });
            setPermsUser(null);
            loadUsers();
        } catch {
            alert('Failed to reset permissions');
        } finally {
            setPermsLoading(false);
        }
    };

    const roleColors: Record<string, string> = {
        ADMIN: 'badge-purple',
        PORTFOLIO_MANAGER: 'badge-info',
        COLLECTIONS_OFFICER: 'badge-warning',
        ACCOUNTANT: 'badge-success',
        UNDERWRITER: 'badge-error',
        CLIENT: 'badge-gray',
    };

    const roleLabel: Record<string, string> = {
        ADMIN: 'Admin',
        PORTFOLIO_MANAGER: 'Portfolio Manager',
        COLLECTIONS_OFFICER: 'Collections Officer',
        ACCOUNTANT: 'Accountant',
        UNDERWRITER: 'Underwriter',
        CLIENT: 'Client',
    };

    return (
        <div>
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">System Users ({users.length})</h3>
                    <button className="btn btn-primary" onClick={openNew}>+ New User</button>
                </div>
                <div className="table-container">
                    {loading ? (
                        <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Permissions</th>
                                    <th>Status</th>
                                    <th>Last Login</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map(user => (
                                    <tr key={user.id}>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                                <div style={{
                                                    width: 36, height: 36, borderRadius: '50%',
                                                    background: 'linear-gradient(135deg, var(--primary-500), var(--primary-700))',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    color: 'white', fontWeight: 700, fontSize: 14, flexShrink: 0,
                                                }}>
                                                    {(user.first_name?.[0] || user.username[0]).toUpperCase()}
                                                </div>
                                                <div>
                                                    <div style={{ fontWeight: 600 }}>{user.first_name} {user.last_name}</div>
                                                    <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>@{user.username}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>{user.email}</td>
                                        <td><span className={`badge ${roleColors[user.role] || 'badge-gray'}`}>{roleLabel[user.role] || user.role}</span></td>
                                        <td>
                                            {user.custom_permissions?.length > 0
                                                ? <span className="badge badge-warning" title={user.custom_permissions.join(', ')}>Custom ({user.custom_permissions.length})</span>
                                                : <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>Role defaults</span>
                                            }
                                        </td>
                                        <td><span className={`badge ${user.is_active ? 'badge-success' : 'badge-error'}`}>{user.is_active ? 'Active' : 'Inactive'}</span></td>
                                        <td style={{ fontSize: 13, color: 'var(--gray-400)' }}>{user.last_login?.split('T')[0] || 'Never'}</td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 6 }}>
                                                <button className="btn btn-secondary btn-sm" onClick={() => openEdit(user)}>Edit</button>
                                                <button className="btn btn-secondary btn-sm" onClick={() => openPerms(user)}>Permissions</button>
                                                <button className="btn btn-secondary btn-sm" onClick={() => openReset(user)} title="Reset password">🔑 Reset PW</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {/* ---- Create / Edit User Modal ---- */}
            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="modal-title">{editUser ? 'Edit User' : 'New User'}</h3>
                            <button className="btn btn-secondary btn-icon" onClick={() => setShowModal(false)}>✕</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-grid">
                                <div className="form-group">
                                    <label className="form-label">First Name</label>
                                    <input className="form-control" value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Last Name</label>
                                    <input className="form-control" value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Username *</label>
                                    <input className="form-control" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} disabled={!!editUser} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Email *</label>
                                    <input className="form-control" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Role *</label>
                                    <select className="form-control" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
                                        <option value="ADMIN">Admin</option>
                                        <option value="PORTFOLIO_MANAGER">Portfolio Manager</option>
                                        <option value="COLLECTIONS_OFFICER">Collections Officer</option>
                                        <option value="ACCOUNTANT">Accountant</option>
                                        <option value="UNDERWRITER">Underwriter</option>
                                        <option value="CLIENT">Client</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">{editUser ? 'New Password (leave blank to keep)' : 'Password *'}</label>
                                    <input className="form-control" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
                                </div>
                            </div>
                            {editUser && (
                                <div className="form-group">
                                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                        <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
                                        <span className="form-label" style={{ margin: 0 }}>Active Account</span>
                                    </label>
                                </div>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleSave}>Save User</button>
                        </div>
                    </div>
                </div>
            )}

            {/* ---- Reset Password Modal ---- */}
            {resetUser && (
                <div className="modal-overlay" onClick={() => setResetUser(null)}>
                    <div className="modal" style={{ maxWidth: 400 }} onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div>
                                <h3 className="modal-title">Reset Password</h3>
                                <div style={{ fontSize: 13, color: 'var(--gray-400)', marginTop: 2 }}>
                                    {resetUser.first_name} {resetUser.last_name} &mdash; @{resetUser.username}
                                </div>
                            </div>
                            <button className="btn btn-secondary btn-icon" onClick={() => setResetUser(null)}>✕</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label className="form-label">New Password</label>
                                <input
                                    className="form-control"
                                    type="password"
                                    value={resetPassword}
                                    onChange={e => setResetPassword(e.target.value)}
                                    placeholder="Min. 8 characters"
                                    autoFocus
                                />
                                {resetPassword.length > 0 && resetPassword.length < 8 && (
                                    <div style={{ fontSize: 12, color: 'var(--error)', marginTop: 4 }}>Password must be at least 8 characters</div>
                                )}
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setResetUser(null)}>Cancel</button>
                            <button
                                className="btn btn-primary"
                                onClick={handleResetPassword}
                                disabled={resetLoading || resetPassword.length < 8}
                            >
                                {resetLoading ? <span className="loading-spinner"></span> : null}
                                Reset Password
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ---- Permissions Modal ---- */}
            {permsUser && (
                <div className="modal-overlay" onClick={() => setPermsUser(null)}>
                    <div className="modal" style={{ maxWidth: 560 }} onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div>
                                <h3 className="modal-title">Manage Permissions</h3>
                                <div style={{ fontSize: 13, color: 'var(--gray-400)', marginTop: 2 }}>
                                    @{permsUser.username} &mdash; <span className={`badge ${roleColors[permsUser.role] || 'badge-gray'}`} style={{ fontSize: 11 }}>{roleLabel[permsUser.role] || permsUser.role}</span>
                                </div>
                            </div>
                            <button className="btn btn-secondary btn-icon" onClick={() => setPermsUser(null)}>✕</button>
                        </div>

                        <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                            {/* Info banner */}
                            <div style={{
                                background: permsUser.custom_permissions?.length > 0 ? 'var(--warning-50, #fffbeb)' : 'var(--primary-50)',
                                border: `1px solid ${permsUser.custom_permissions?.length > 0 ? 'var(--warning-200, #fde68a)' : 'var(--primary-200)'}`,
                                borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 13,
                                color: permsUser.custom_permissions?.length > 0 ? 'var(--warning-700, #92400e)' : 'var(--primary-700)',
                            }}>
                                {permsUser.custom_permissions?.length > 0
                                    ? `This user has ${permsUser.custom_permissions.length} custom permission(s) overriding their role defaults.`
                                    : `Using role defaults for ${roleLabel[permsUser.role] || permsUser.role}. Saving will apply these as custom permissions.`
                                }
                            </div>

                            {/* Permission groups */}
                            {PERMISSION_GROUPS.map(group => {
                                const keys = group.items.map(i => i.key);
                                const allChecked = keys.every(k => permsSelected.includes(k));
                                const someChecked = keys.some(k => permsSelected.includes(k));

                                return (
                                    <div key={group.group} style={{ marginBottom: 20 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                                            <span style={{ fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--gray-500)' }}>
                                                {group.group}
                                            </span>
                                            <button
                                                className="btn btn-secondary btn-sm"
                                                style={{ fontSize: 11, padding: '2px 8px' }}
                                                onClick={() => toggleGroup(keys)}
                                            >
                                                {allChecked ? 'Deselect All' : someChecked ? 'Select All' : 'Select All'}
                                            </button>
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                            {group.items.map(item => (
                                                <label
                                                    key={item.key}
                                                    style={{
                                                        display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                                                        padding: '8px 12px', borderRadius: 6, border: '1px solid var(--gray-200)',
                                                        background: permsSelected.includes(item.key) ? 'var(--primary-50)' : 'white',
                                                        borderColor: permsSelected.includes(item.key) ? 'var(--primary-300)' : 'var(--gray-200)',
                                                        transition: 'all 0.15s',
                                                    }}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={permsSelected.includes(item.key)}
                                                        onChange={() => togglePerm(item.key)}
                                                        style={{ accentColor: 'var(--primary-600)' }}
                                                    />
                                                    <span style={{ fontSize: 13, fontWeight: permsSelected.includes(item.key) ? 600 : 400 }}>
                                                        {item.label}
                                                    </span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
                            <button
                                className="btn btn-secondary"
                                onClick={resetToRoleDefaults}
                                disabled={permsLoading}
                                title="Clears custom permissions and reverts to role defaults"
                            >
                                Reset to Role Defaults
                            </button>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button className="btn btn-secondary" onClick={() => setPermsUser(null)} disabled={permsLoading}>Cancel</button>
                                <button className="btn btn-primary" onClick={savePerms} disabled={permsLoading}>
                                    {permsLoading ? <span className="loading-spinner"></span> : null}
                                    Save Permissions
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

const MOCK_USERS = [
    { id: 1, username: 'admin',       email: 'admin@intzam.com',       first_name: 'System',     last_name: 'Admin',   role: 'ADMIN',               is_active: true, last_login: '2025-02-18T08:00:00Z', custom_permissions: [] },
    { id: 2, username: 'portfolio',   email: 'portfolio@intzam.com',   first_name: 'Portfolio',  last_name: 'Manager', role: 'PORTFOLIO_MANAGER',   is_active: true, last_login: '2025-02-18T09:00:00Z', custom_permissions: [] },
    { id: 3, username: 'collections', email: 'collections@intzam.com', first_name: 'Collections',last_name: 'Officer', role: 'COLLECTIONS_OFFICER', is_active: true, last_login: '2025-02-17T14:00:00Z', custom_permissions: [] },
    { id: 4, username: 'finance',     email: 'finance@intzam.com',     first_name: 'Finance',    last_name: 'Manager', role: 'ACCOUNTANT',          is_active: true, last_login: null,                   custom_permissions: [] },
    { id: 5, username: 'underwriter', email: 'underwriter@intzam.com', first_name: 'Loan',       last_name: 'Underwriter', role: 'UNDERWRITER',     is_active: true, last_login: '2025-02-18T07:30:00Z', custom_permissions: [] },
];
