import { useState } from 'react';
import Sidebar from './Sidebar';
import { effectivePermissions } from '../../permissions';
import Header from './Header';
import DashboardPage from '../../pages/DashboardPage';
import ClientsPage from '../../pages/ClientsPage';
import QualifiedBasePage from '../../pages/QualifiedBasePage';
import ProductsPage from '../../pages/ProductsPage';
import LoansPage from '../../pages/LoansPage';
import UnderwritingPage from '../../pages/UnderwritingPage';
import CollectionsPage from '../../pages/CollectionsPage';
import AccountingPage from '../../pages/AccountingPage';
import ReportsPage from '../../pages/ReportsPage';
import UsersPage from '../../pages/UsersPage';
import AuditLogsPage from '../../pages/AuditLogsPage';
import KYCBuilderPage from '../../pages/KYCBuilderPage';
import KYCSubmissionsPage from '../../pages/KYCSubmissionsPage';
import SettingsPage from '../../pages/SettingsPage';

interface AdminLayoutProps {
    user: any;
    onLogout: () => void;
}

export type Module = 'dashboard' | 'clients' | 'qualified_base' | 'products' | 'loans' | 'underwriting' | 'collections' | 'disbursements' | 'accounting' | 'reports' | 'users' | 'audit_logs' | 'kyc_builder' | 'kyc_submissions' | 'settings';

export default function AdminLayout({ user, onLogout }: AdminLayoutProps) {
    const [activeModule, setActiveModule] = useState<Module>('dashboard');
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    const perms = effectivePermissions(user);

    const renderModule = () => {
        switch (activeModule) {
            case 'dashboard': return <DashboardPage />;
            case 'clients': return <ClientsPage />;
            case 'qualified_base': return <QualifiedBasePage />;
            case 'products': return <ProductsPage />;
            case 'loans': return <LoansPage userPermissions={perms} />;
            case 'underwriting': return <UnderwritingPage userPermissions={perms} />;
            case 'collections': return <CollectionsPage userRole={user.role} />;
            case 'disbursements': return <AccountingPage initialTab="disbursements" />;
            case 'accounting': return <AccountingPage />;
            case 'reports': return <ReportsPage userPermissions={perms} />;
            case 'users': return <UsersPage />;
            case 'audit_logs': return <AuditLogsPage />;
            case 'kyc_builder': return <KYCBuilderPage />;
            case 'kyc_submissions': return <KYCSubmissionsPage userPermissions={perms} />;
            case 'settings': return <SettingsPage />;
            default: return <DashboardPage />;
        }
    };

    const moduleTitles: Record<Module, string> = {
        dashboard: 'Dashboard',
        clients: 'Client Management',
        qualified_base: 'Qualified Base (KYC)',
        products: 'Loan Products',
        loans: 'Loan Servicing',
        underwriting: 'Underwriting',
        collections: 'Collections',
        disbursements: 'Disbursements Queue',
        accounting: 'Accounting',
        reports: 'Reports Center',
        users: 'User Management',
        audit_logs: 'System Audit Logs',
        kyc_builder: 'KYC Form Builder',
        kyc_submissions: 'Client KYC Reviews',
        settings: 'System Settings',
    };

    return (
        <div className="app-layout">
            <Sidebar
                activeModule={activeModule}
                onModuleChange={setActiveModule}
                collapsed={sidebarCollapsed}
                userPermissions={effectivePermissions(user)}
            />
            <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
                <Header
                    title={moduleTitles[activeModule]}
                    user={user}
                    onLogout={onLogout}
                    onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
                    sidebarCollapsed={sidebarCollapsed}
                />
                <div className="page-content animate-in">
                    {renderModule()}
                </div>
            </div>
        </div>
    );
}
