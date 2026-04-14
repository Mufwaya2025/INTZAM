interface HeaderProps {
    title: string;
    user: any;
    onLogout: () => void;
    onToggleSidebar: () => void;
    sidebarCollapsed: boolean;
}

export default function Header({ title, user, onLogout, onToggleSidebar, sidebarCollapsed }: HeaderProps) {
    const initials = user.name?.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2) || 'U';

    const roleColors: Record<string, string> = {
        ADMIN: '#7c3aed',
        PORTFOLIO_MANAGER: '#2563eb',
        COLLECTIONS_OFFICER: '#d97706',
        ACCOUNTANT: '#059669',
        UNDERWRITER: '#dc2626',
        CLIENT: '#6b7280',
    };

    const roleLabels: Record<string, string> = {
        ADMIN: 'Administrator',
        PORTFOLIO_MANAGER: 'Portfolio Manager',
        COLLECTIONS_OFFICER: 'Collections Officer',
        ACCOUNTANT: 'Accountant',
        UNDERWRITER: 'Underwriter',
        CLIENT: 'Client',
    };

    return (
        <header className={`header ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
            <div className="header-left">
                <button
                    onClick={onToggleSidebar}
                    className="btn btn-secondary btn-icon"
                    title="Toggle sidebar"
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="3" y1="6" x2="21" y2="6" />
                        <line x1="3" y1="12" x2="21" y2="12" />
                        <line x1="3" y1="18" x2="21" y2="18" />
                    </svg>
                </button>
                <h1 className="header-title">{title}</h1>
            </div>

            <div className="header-right">
                <div style={{
                    padding: '4px 12px',
                    borderRadius: '100px',
                    background: `${roleColors[user.role]}20`,
                    color: roleColors[user.role],
                    fontSize: 12,
                    fontWeight: 600,
                }}>
                    {roleLabels[user.role] || user.role}
                </div>

                <div className="header-user">
                    <div className="user-avatar">{initials}</div>
                    <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--gray-800)' }}>
                            {user.name || user.username}
                        </div>
                    </div>
                </div>

                <button
                    onClick={onLogout}
                    className="btn btn-secondary btn-sm"
                    title="Logout"
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                        <polyline points="16 17 21 12 16 7" />
                        <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    Logout
                </button>
            </div>
        </header>
    );
}
