import { useState } from 'react';
import { Home, FileText, CreditCard, Clock, User } from 'lucide-react';
import DashboardPage from '../pages/DashboardPage';
import LoansPage from '../pages/LoansPage';
import ApplyPage from '../pages/ApplyPage';
import HistoryPage from '../pages/HistoryPage';
import ProfilePage from '../pages/ProfilePage';
import LoanDetailPage from '../pages/LoanDetailPage';
import PaymentPage from '../pages/PaymentPage';
import KYCPage from '../pages/KYCPage';

export type Page =
    | { name: 'dashboard' }
    | { name: 'loans' }
    | { name: 'apply' }
    | { name: 'kyc' }
    | { name: 'history' }
    | { name: 'profile' }
    | { name: 'loan-detail'; loanId: number }
    | { name: 'payment'; loanId: number };

export default function AppShell() {
    const [page, setPage] = useState<Page>({ name: 'dashboard' });

    const navigate = (p: Page) => {
        setPage(p);
        window.scrollTo(0, 0);
    };

    const renderPage = () => {
        switch (page.name) {
            case 'dashboard':
                return <DashboardPage navigate={navigate} />;
            case 'loans':
                return <LoansPage navigate={navigate} />;
            case 'apply':
                return <ApplyPage navigate={navigate} />;
            case 'kyc':
                return <KYCPage navigate={navigate} />;
            case 'history':
                return <HistoryPage navigate={navigate} />;
            case 'profile':
                return <ProfilePage navigate={navigate} />;
            case 'loan-detail':
                return <LoanDetailPage loanId={page.loanId} navigate={navigate} />;
            case 'payment':
                return <PaymentPage loanId={page.loanId} navigate={navigate} />;
            default:
                return <DashboardPage navigate={navigate} />;
        }
    };

    const activeTab = page.name === 'loan-detail' || page.name === 'payment' ? 'loans' : page.name;

    return (
        <div className="app-shell">
            <div className="animate-in" key={page.name + ('loanId' in page ? page.loanId : '')}>
                {renderPage()}
            </div>

            {page.name !== 'loan-detail' && page.name !== 'payment' && (
                <nav className="bottom-nav">
                    <div className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => navigate({ name: 'dashboard' })}>
                        <Home className="nav-tab-icon" />
                        <span className="nav-tab-label">Home</span>
                    </div>
                    <div className={`nav-tab ${activeTab === 'loans' ? 'active' : ''}`} onClick={() => navigate({ name: 'loans' })}>
                        <FileText className="nav-tab-icon" />
                        <span className="nav-tab-label">Loans</span>
                    </div>
                    <div className="nav-tab" onClick={() => navigate({ name: 'apply' })}>
                        <div className="nav-fab">
                            <CreditCard size={22} />
                        </div>
                    </div>
                    <div className={`nav-tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => navigate({ name: 'history' })}>
                        <Clock className="nav-tab-icon" />
                        <span className="nav-tab-label">History</span>
                    </div>
                    <div className={`nav-tab ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => navigate({ name: 'profile' })}>
                        <User className="nav-tab-icon" />
                        <span className="nav-tab-label">Profile</span>
                    </div>
                </nav>
            )}
        </div>
    );
}
