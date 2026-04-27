import type { Module } from './AdminLayout';

interface SidebarProps {
    activeModule: Module;
    onModuleChange: (module: Module) => void;
    collapsed: boolean;
    userPermissions: string[];
}

const NAV_ITEMS = [
    {
        section: 'Overview',
        items: [
            { id: 'dashboard',       label: 'Dashboard',          icon: '📊' },
        ],
    },
    {
        section: 'Operations',
        items: [
            { id: 'clients',         label: 'Clients',            icon: '👥' },
            { id: 'qualified_base',  label: 'Qualified Base',     icon: '✅' },
            { id: 'products',        label: 'Loan Products',      icon: '📦' },
            { id: 'loans',           label: 'Loan Servicing',     icon: '💰' },
            { id: 'underwriting',    label: 'Underwriting',       icon: '✅' },
            { id: 'collections',     label: 'Collections',        icon: '📞' },
            { id: 'kyc_builder',     label: 'KYC Form Builder',   icon: '📝' },
            { id: 'kyc_submissions', label: 'Client KYC Reviews', icon: '🔍' },
        ],
    },
    {
        section: 'Finance',
        items: [
            { id: 'disbursements', label: 'Disbursements', icon: '💸' },
            { id: 'cgrate',        label: 'CGRate',        icon: '📲' },
            { id: 'accounting',    label: 'Accounting',    icon: '📒' },
            { id: 'reports',       label: 'Reports',       icon: '📈' },
        ],
    },
    {
        section: 'Admin',
        items: [
            { id: 'users',      label: 'Users',           icon: '👤' },
            { id: 'audit_logs', label: 'Audit Logs',      icon: '📋' },
            { id: 'settings',   label: 'System Settings', icon: '⚙️' },
        ],
    },
];

export default function Sidebar({ activeModule, onModuleChange, collapsed, userPermissions = [] }: SidebarProps) {
    return (
        <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">IZ</div>
                {!collapsed && (
                    <div className="sidebar-logo-text">Int<span>Zam</span> LMS</div>
                )}
            </div>

            <nav className="sidebar-nav">
                {NAV_ITEMS.map(section => {
                    const visibleItems = section.items.filter(item => userPermissions.includes(item.id));
                    if (visibleItems.length === 0) return null;

                    return (
                        <div key={section.section}>
                            {!collapsed && (
                                <div className="nav-section-title">{section.section}</div>
                            )}
                            {visibleItems.map(item => (
                                <div
                                    key={item.id}
                                    className={`nav-item ${activeModule === item.id ? 'active' : ''}`}
                                    onClick={() => onModuleChange(item.id as Module)}
                                    title={collapsed ? item.label : undefined}
                                >
                                    <span className="nav-item-icon" style={{ fontSize: 18 }}>{item.icon}</span>
                                    {!collapsed && <span className="nav-item-label">{item.label}</span>}
                                </div>
                            ))}
                        </div>
                    );
                })}
            </nav>

            <div className="sidebar-footer">
                <div className="nav-item" style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>
                    <span style={{ fontSize: 16 }}>🔒</span>
                    {!collapsed && <span>Secured System</span>}
                </div>
            </div>
        </div>
    );
}
