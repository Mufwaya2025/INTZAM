# IntZam LMS - Key Components Deep Dive

This document provides an in-depth explanation of each major component in the IntZam LMS application, including how they work, their internal logic, state management, and interactions.

---

## Table of Contents

1. [App.tsx - Root Component](#apptsx---root-component)
2. [LandingPage.tsx - Authentication](#landingpagetsx---authentication)
3. [ClientPWA.tsx - Client Portal](#clientpwatsx---client-portal)
4. [AdminDashboard.tsx - Staff Interface](#admindashboardtsx---staff-interface)
5. [Underwriting.tsx - Loan Approval](#underwritingtsx---loan-approval)
6. [LoanServicing.tsx - Active Loan Management](#loanservicingtsx---active-loan-management)
7. [Collections.tsx - Debt Collection](#collectionstsx---debt-collection)
8. [Accounting.tsx - Financial Management](#accountingtsx---financial-management)
9. [ReportsCenter.tsx - Report Generation](#reportscentertsx---report-generation)

---

## App.tsx - Root Component

### Purpose
The root component that manages application state and routing between different views (Landing, Admin, Client).

### State Management

```typescript
const [activeView, setActiveView] = useState<'landing' | 'admin' | 'client'>('landing');
const [currentUser, setCurrentUser] = useState<Client | null>(null);
const [staffRole, setStaffRole] = useState<UserRole>(UserRole.ADMIN);
```

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│                      App Component                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ LandingPage  │    │AdminDashboard│    │ClientPWA  │ │
│  │              │    │              │    │           │ │
│  │ - Login      │    │ - Products   │    │ - Apply   │ │
│  │ - Register   │    │ - Users      │    │ - Pay     │ │
│  │ - Role Select│    │ - Reports    │    │ - Manage  │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│         ▲                   ▲                  ▲        │
│         │                   │                  │        │
│         └───────────────────┼──────────────────┘        │
│                             │                            │
│                    State Management                      │
│         • activeView (which screen to show)              │
│         • currentUser (logged in client)                 │
│         • staffRole (admin user role)                    │
└─────────────────────────────────────────────────────────┘
```

### Key Functions

| Function | Purpose | Triggered By |
|----------|---------|--------------|
| `handleClientLogin(client)` | Sets client user and switches to client view | Client successful login |
| `handleStaffLogin(role)` | Sets staff role and switches to admin view | Staff successful login |
| `handleLogout()` | Clears user state and returns to landing | Logout button click |

### Rendering Logic

```typescript
{activeView === 'landing' && <LandingPage ... />}
{activeView === 'admin' && <AdminDashboard ... />}
{activeView === 'client' && <ClientPWA ... />}
```

### Styling
Includes custom animation styles for smooth transitions between views:
- `slideInRight`: 0.3s cubic-bezier animation for view changes

---

## LandingPage.tsx - Authentication

### Purpose
Handles user authentication (login) and new client registration with a multi-step KYC flow.

### State Management

```typescript
// Mode switching
const [mode, setMode] = useState<'login' | 'register'>('login');

// Login state
const [email, setEmail] = useState('');
const [password, setPassword] = useState('');
const [loading, setLoading] = useState(false);
const [error, setError] = useState('');

// Registration multi-step state
const [step, setStep] = useState(1);
const [regData, setRegData] = useState({...});
const [idFiles, setIdFiles] = useState({ front: false, back: false });
```

### Login Flow

```
User enters credentials
        ↓
Email pattern detection
        ↓
┌───────────────────────────────────────┐
│  Email contains...    → Role assigned │
├───────────────────────────────────────┤
│  "admin"             → ADMIN          │
│  "portfolio"         → PORTFOLIO_MANAGER
│  "collections"       → COLLECTIONS_OFFICER
│  "finance"/"accountant" → ACCOUNTANT  │
│  "underwriter"       → UNDERWRITER    │
│  (none of above)     → Client lookup  │
└───────────────────────────────────────┘
        ↓
authenticateClient(email) - Mock DB lookup
        ↓
onLoginClient(client) - Pass to App.tsx
```

### Registration Flow (3 Steps)

```
Step 1: Identity Details
├── Full Name
├── Email Address
└── Phone Number
        ↓ (validation: name & email required)
Step 2: KYC & Financials
├── NRC/ID Number
├── Employment Status (dropdown)
├── Monthly Income
├── Next of Kin Name
├── Next of Kin Relation
└── Next of Kin Phone
        ↓ (validation: all fields required)
Step 3: Verification
├── NRC Front Photo Upload (simulated)
└── NRC Back Photo Upload (simulated)
        ↓ (both uploads required)
registerClient(regData) - Create account
        ↓
onLoginClient(newClient) - Auto login
```

### Document Upload Simulation

```typescript
const simulateUpload = (docName: string) => {
  setUploadingDoc(docName);
  setTimeout(() => {
    setUploadedDocs(prev => ({ ...prev, [docName]: true }));
    setUploadingDoc(null);
  }, 1500);
};
```

### Quick Access Buttons

Pre-configured credentials for demo purposes:

```typescript
const fillCredentials = (type: string) => {
  switch(type) {
    case 'admin': setEmail('admin@intzam.com'); break;
    case 'client': setEmail('alice@example.com'); break;
    case 'portfolio': setEmail('portfolio@intzam.com'); break;
    // ... etc
  }
};
```

---

## ClientPWA.tsx - Client Portal

### Purpose
Mobile-first progressive web app for clients to manage their loans, apply for new loans, and make payments.

### State Management

```typescript
// Navigation
const [view, setView] = useState<'dashboard' | 'apply' | 'pay' | 'manage'>('dashboard');

// Data
const [clientData, setClientData] = useState<Client | null>(null);
const [loans, setLoans] = useState<LoanApplication[]>([]);
const [products, setProducts] = useState<LoanProduct[]>([]);

// Application form
const [selectedProductId, setSelectedProductId] = useState('');
const [amount, setAmount] = useState(1000);
const [term, setTerm] = useState(3);
const [purpose, setPurpose] = useState('');

// Document uploads
const [uploadedDocs, setUploadedDocs] = useState<Record<string, boolean>>({});

// Payment
const [payAmount, setPayAmount] = useState(0);
const [selectedLoanId, setSelectedLoanId] = useState('');
const [isSettlement, setIsSettlement] = useState(false);

// Rollover modal
const [isRolloverModalOpen, setIsRolloverModalOpen] = useState(false);
const [rolloverDays, setRolloverDays] = useState(14);
```

### View Architecture

```
┌────────────────────────────────────────────┐
│              ClientPWA Views                │
├────────────────────────────────────────────┤
│                                            │
│  Dashboard                                 │
│  ├── Active balance overview               │
│  ├── Loan cards (Active/Overdue/Pending)   │
│  ├── Quick actions (Apply, Pay, Manage)    │
│  └── Tier status banner                    │
│                                            │
│  Apply                                     │
│  ├── Product selection (horizontal scroll) │
│  ├── Amount slider with tier limits        │
│  ├── Term selector                         │
│  ├── Purpose dropdown                      │
│  ├── Document upload grid                  │
│  └── Cost breakdown display                │
│                                            │
│  Pay                                       │
│  ├── Loan selection                        │
│  ├── Payment type (Regular/Settlement)     │
│  ├── Amount input                          │
│  └── Mobile money simulation               │
│                                            │
│  Manage                                    │
│  ├── Loan details                          │
│  ├── Payment history                       │
│  ├── Rollover request                      │
│  ├── Early settlement quote                │
│  └── Statement download                    │
└────────────────────────────────────────────┘
```

### Loan Application Process

```typescript
const handleApply = async (e: React.FormEvent) => {
  e.preventDefault();
  
  // 1. Get selected product
  const product = products.find(p => p.id === selectedProductId);
  
  // 2. Collect uploaded documents
  const uploadedDocNames = Object.keys(uploadedDocs)
    .filter(key => uploadedDocs[key]);
  
  // 3. Calculate effective rate based on tier
  const currentTier = clientData?.tier || ClientTier.BRONZE;
  const tierConfig = product.tiers.find(t => t.tier === currentTier);
  const effectiveRate = tierConfig?.interestRate || product.interestRate;
  
  // 4. Submit application
  await submitLoanApplication({
    clientId,
    clientName,
    productId: selectedProductId,
    amount,
    termMonths: term,
    purpose,
    interestRate: effectiveRate,
    documents: uploadedDocNames
  });
};
```

### Tier-Based Price Compression

```typescript
// Calculate tier-specific limits and rates
const currentTier = clientData?.tier || ClientTier.BRONZE;
const tierConfig = activeProduct?.tiers?.find(t => t.tier === currentTier);

const effectiveRate = tierConfig?.interestRate || 25;  // Default to base rate
const limitMultiplier = tierConfig?.maxLimitMultiplier || 1;

// Apply multiplier to product max amount
const tierMaxAmount = (activeProduct?.maxAmount || 0) * limitMultiplier;
```

### Rollover Eligibility Logic

```
┌─────────────────────────────────────────────────────┐
│            Rollover Eligibility Check               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Product Config:                                    │
│  • rolloverMinPrincipalPaidPercent: 30%             │
│  • rolloverExtensionDays: 14                        │
│  • rolloverInterestRate: 4%                         │
│                                                     │
│  Client Status:                                     │
│  • Original Principal: $10,000                      │
│  • Amount Repaid: $3,500                            │
│                                                     │
│  Calculation:                                       │
│  Required = $10,000 × 30% = $3,000                  │
│  Progress = $3,500 / $3,000 = 116% ✓                │
│                                                     │
│  Result: ELIGIBLE                                   │
└─────────────────────────────────────────────────────┘
```

### Rollover Fee Calculation

```typescript
const outstanding = loan.totalRepayable - loan.repaidAmount;
const fixedFee = 50;  // Base fee
const ratio = rolloverDays / defaultExtensionDays;  // e.g., 14/14 = 1
const interestFee = outstanding * (rolloverRate / 100) * ratio;
const rolloverFee = fixedFee + interestFee;
```

### Payment Flow

```
Select Payment Type
        ↓
┌───────────────────┐
│ Regular Payment   │  → Pay next installment amount
│ Early Settlement  │  → Get payoff quote, pay full balance
└───────────────────┘
        ↓
Enter Amount
        ↓
Confirm Payment
        ↓
makeRepayment(loanId, amount)  OR  settleLoan(loanId, amount)
        ↓
Update UI → Return to Dashboard
```

---

## AdminDashboard.tsx - Staff Interface

### Purpose
Main administrative interface with role-based access control for staff members.

### State Management

```typescript
// Navigation
const [activeModule, setActiveModule] = useState<Module>(Module.PRODUCTS);
const [sidebarOpen, setSidebarOpen] = useState(true);

// Data
const [products, setProducts] = useState<LoanProduct[]>([]);
const [loans, setLoans] = useState<LoanApplication[]>([]);
const [staff, setStaff] = useState<Staff[]>([]);
const [roles, setRoles] = useState<Role[]>([]);

// Modals
const [isProductModalOpen, setIsProductModalOpen] = useState(false);
const [isUserModalOpen, setIsUserModalOpen] = useState(false);
const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
```

### Module Structure

```typescript
enum Module {
  DASHBOARD = 'dashboard',
  PRODUCTS = 'products',
  USERS = 'users',
  UNDERWRITING = 'underwriting',
  LOAN_SERVICING = 'loanServicing',
  COLLECTIONS = 'collections',
  ACCOUNTING = 'accounting',
  REPORTS = 'reports'
}
```

### Permission Checking

```typescript
const hasPermission = (permission: Permission): boolean => {
  return ROLE_PERMISSIONS[userRole]?.includes(permission) || false;
};

// Usage in rendering
{hasPermission('APPROVE_LOAN') && (
  <button onClick={handleApprove}>Approve</button>
)}
```

### ProductsView Component

Handles loan product configuration:

```typescript
const ProductsView = ({ products, setProducts }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editProduct, setEditProduct] = useState<Partial<LoanProduct>>({});
  
  const handleSaveProduct = async () => {
    if (editProduct.id) {
      await updateProduct(editProduct as LoanProduct);
    } else {
      await createProduct(editProduct as Omit<LoanProduct, 'id'>);
    }
    // Refresh list
    const p = await getProducts();
    setProducts(p);
    setIsEditing(false);
  };
  
  // Rate component updates
  const updateRateComponent = (field: keyof LoanProduct, value: number) => {
    const current = { ...editProduct, [field]: value };
    const nominal = field === 'nominalInterestRate' 
      ? value 
      : (current.nominalInterestRate || 0);
    const facilitation = field === 'creditFacilitationFee' 
      ? value 
      : (current.creditFacilitationFee || 0);
    const processing = field === 'processingFee' 
      ? value 
      : (current.processingFee || 0);
    
    // Auto-calculate total rate
    setEditProduct({
      ...current,
      interestRate: nominal + facilitation + processing
    });
  };
};
```

### UserManagement Component

Manages staff and roles:

```typescript
const UserManagement = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'roles'>('users');
  
  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    const [staffList, rolesList] = await Promise.all([
      getStaffList(),
      getRoles()
    ]);
    setStaff(staffList);
    setRoles(rolesList);
  };
  
  // Permission toggle for role editing
  const togglePermission = (perm: Permission) => {
    const currentPerms = editRole.permissions || [];
    if (currentPerms.includes(perm)) {
      setEditRole({ 
        ...editRole, 
        permissions: currentPerms.filter(p => p !== perm) 
      });
    } else {
      setEditRole({ 
        ...editRole, 
        permissions: [...currentPerms, perm] 
      });
    }
  };
};
```

### Module Rendering

```typescript
const renderModule = () => {
  switch (activeModule) {
    case Module.PRODUCTS:
      return <ProductsView products={products} setProducts={setProducts} />;
    case Module.USERS:
      return <UserManagement />;
    case Module.UNDERWRITING:
      return <Underwriting userRole={userRole} />;
    case Module.LOAN_SERVICING:
      return <LoanServicing userRole={userRole} />;
    case Module.COLLECTIONS:
      return <Collections userRole={userRole} />;
    case Module.ACCOUNTING:
      return <Accounting />;
    case Module.REPORTS:
      return <ReportsCenter userRole={userRole} />;
    default:
      return <Dashboard />;
  }
};
```

---

## Underwriting.tsx - Loan Approval

### Purpose
Loan application review and approval workflow with AI-powered risk analysis.

### State Management

```typescript
const [applications, setApplications] = useState<LoanApplication[]>([]);
const [selectedApplication, setSelectedApplication] = useState<string | null>(null);
const [aiAnalysis, setAiAnalysis] = useState<string>('');
const [loadingAnalysis, setLoadingAnalysis] = useState(false);
const [filterStatus, setFilterStatus] = useState<'PENDING' | 'APPROVED' | 'REJECTED'>('PENDING');
```

### Application Review Flow

```
┌────────────────────────────────────────────────────────┐
│              Underwriting Workflow                      │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1. Application Queue                                  │
│     └── Filter by status (Pending/Approved/Rejected)   │
│                                                        │
│  2. Select Application                                 │
│     └── View client details, loan details, documents   │
│                                                        │
│  3. AI Risk Analysis (Optional)                        │
│     └── Call Gemini API with loan + client data        │
│     └── Display risk assessment                        │
│                                                        │
│  4. Decision                                           │
│     ├── Approve → Update status, schedule disbursement │
│     ├── Reject  → Update status, add rejection reason  │
│     └── Request More Info → Add notes, keep pending    │
│                                                        │
│  5. Post-Decision                                      │
│     └── Refresh queue, notify client                   │
└────────────────────────────────────────────────────────┘
```

### AI Risk Analysis Integration

```typescript
const handleAiAnalysis = async () => {
  if (!selectedApplication) return;
  
  setLoadingAnalysis(true);
  
  try {
    const app = applications.find(a => a.id === selectedApplication);
    const client = await getClient(app.clientId);
    
    // Call Gemini AI service
    const analysis = await analyzeLoanRisk(app, client);
    setAiAnalysis(analysis);
  } catch (error) {
    console.error('AI Analysis failed:', error);
    setAiAnalysis('Unable to perform AI analysis.');
  } finally {
    setLoadingAnalysis(false);
  }
};
```

### Approval/Rejection Logic

```typescript
const handleApprove = async () => {
  await updateLoanStatus(selectedApplication, LoanStatus.APPROVED);
  await refreshApplications();
  setSelectedApplication(null);
};

const handleReject = async (reason: string) => {
  await updateLoanStatus(selectedApplication, LoanStatus.REJECTED, reason);
  await refreshApplications();
  setSelectedApplication(null);
};
```

---

## LoanServicing.tsx - Active Loan Management

### Purpose
Manage active loans including repayments, rollovers, and settlements.

### State Management

```typescript
const [activeLoans, setActiveLoans] = useState<LoanApplication[]>([]);
const [selectedLoan, setSelectedLoan] = useState<string | null>(null);
const [repaymentAmount, setRepaymentAmount] = useState(0);
const [payoffQuote, setPayoffQuote] = useState<PayoffQuote | null>(null);
```

### Key Operations

| Operation | Description | API Call |
|-----------|-------------|----------|
| Post Repayment | Record a payment against active loan | `makeRepayment(loanId, amount)` |
| Early Settlement | Pay off loan early with quote | `getPayoffQuote(loanId)` → `settleLoan(loanId, amount)` |
| Rollover Request | Extend loan term | `performRollover(loanId, extensionDays)` |
| View Schedule | Display amortization schedule | Generated from loan terms |

### Repayment Posting Flow

```
Select Loan
    ↓
Enter Payment Amount
    ↓
Choose Payment Type
├── Regular (next installment)
├── Extra (additional principal)
└── Full Settlement
    ↓
Confirm Payment
    ↓
makeRepayment(loanId, amount)
    ↓
Update Loan Balance
    ↓
Create Transaction Record
    ↓
Check if Loan Complete → Update Status to CLOSED
    ↓
Update Client Tier (if applicable)
```

### Payoff Quote Calculation

```typescript
const handleGetQuote = async () => {
  const quote = await getPayoffQuote(manageLoanId);
  setPayoffQuote(quote);
  // quote includes:
  // - principalOutstanding
  // - interestAccrued
  // - earlyTerminationFee
  // - totalPayoffAmount
  // - savingComparison (interest saved vs continuing)
};
```

---

## Collections.tsx - Debt Collection

### Purpose
Manage overdue loans and collection activities with PTP (Promise to Pay) tracking.

### State Management

```typescript
const [loans, setLoans] = useState<LoanApplication[]>([]);
const [activities, setActivities] = useState<CollectionActivity[]>([]);
const [selectedLoanId, setSelectedLoanId] = useState<string | null>(null);
const [actionType, setActionType] = useState<CollectionActionType>('CALL');
const [notes, setNotes] = useState('');
const [ptpDate, setPtpDate] = useState('');
const [ptpAmount, setPtpAmount] = useState('');

// Filters
const [filterBucket, setFilterBucket] = useState<'ALL' | '1-30' | '31-60' | '61-90' | '90+'>('ALL');
const [searchTerm, setSearchTerm] = useState('');
```

### Collection Queue Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Collections Queue                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Stats Header                                           │
│  ┌──────────────┬──────────────┬──────────────┐        │
│  │ Recovery     │ Target       │ Achievement  │        │
│  │ (Today)      │ (Today)      │ (%)          │        │
│  │ $X,XXX       │ $X,XXX       │ XX%          │        │
│  └──────────────┴──────────────┴──────────────┘        │
│                                                         │
│  Filters                                                │
│  • Search by client name/ID                             │
│  • PAR Bucket: ALL | 1-30 | 31-60 | 61-90 | 90+         │
│                                                         │
│  Loan List (sorted by days overdue DESC)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Client Name          │ Days │ Amount │ Status   │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ John Doe             │ 45   │ $5,000 │ ACTIVE   │   │
│  │ Jane Smith           │ 23   │ $3,200 │ PTP      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Activity Panel (when loan selected)                    │
│  • Client details                                       │
│  • Loan details                                         │
│  • Activity history timeline                            │
│  • Log new activity form                                │
└─────────────────────────────────────────────────────────┘
```

### PAR Bucket Filtering

```typescript
const filteredLoans = loans.filter(l => {
  const days = getDaysOverdue(l);
  let matchesBucket = true;
  
  if (filterBucket === '1-30') 
    matchesBucket = days >= 1 && days <= 30;
  if (filterBucket === '31-60') 
    matchesBucket = days > 30 && days <= 60;
  if (filterBucket === '61-90') 
    matchesBucket = days > 60 && days <= 90;
  if (filterBucket === '90+') 
    matchesBucket = days > 90;
  
  return matchesSearch && matchesBucket;
}).sort((a, b) => getDaysOverdue(b) - getDaysOverdue(a));
```

### Collection Activity Logging

```typescript
const handleLogActivity = async (e: React.FormEvent) => {
  e.preventDefault();
  
  const newActivity = await logCollectionActivity({
    loanId: selectedLoanId,
    action: actionType,  // CALL, SMS, WHATSAPP, EMAIL, FIELD_VISIT, etc.
    agentName: userRole === 'ADMIN' ? 'Administrator' : 'Collections Officer',
    notes: notes,
    outcome: outcome || undefined,
    ptpDate: actionType === 'PTP_PROMISE' ? ptpDate : undefined,
    ptpAmount: actionType === 'PTP_PROMISE' ? Number(ptpAmount) : undefined
  });
  
  // Reset form
  setNotes('');
  setOutcome('');
  setPtpDate('');
  setPtpAmount('');
  
  // Refresh data
  await refreshData();
};
```

### PTP (Promise to Pay) Status Flow

```
┌─────────────┐
│    NONE     │  ← Default state
└──────┬──────┘
       │ Client promises to pay
       ↓
┌─────────────┐
│   ACTIVE    │  ← PTP date/amount recorded
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       │              │              │
  Payment made    Date passed   Date passed
  before date     with payment  without payment
       │              │              │
       ↓              ↓              ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   NONE      │ │   NONE      │ │   BROKEN    │
│ (fulfilled) │ │ (rescheduled)│ │ (escalate)  │
└─────────────┘ └─────────────┘ └─────────────┘
```

### Days Overdue Calculation

```typescript
const getDaysOverdue = (loan: LoanApplication): number => {
  if (loan.status !== LoanStatus.OVERDUE && 
      loan.status !== LoanStatus.ACTIVE) {
    return 0;
  }
  
  const now = new Date();
  const dueDate = new Date(loan.dueDate);
  const diffMs = now.getTime() - dueDate.getTime();
  return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
};
```

---

## Accounting.tsx - Financial Management

### Purpose
Double-entry bookkeeping system with chart of accounts, general ledger, and period-end operations.

### State Management

```typescript
const [view, setView] = useState<'coa' | 'ledger' | 'operations' | 'reconciliation' | 'audit'>('coa');
const [accounts, setAccounts] = useState<LedgerAccount[]>([]);
const [journal, setJournal] = useState<JournalEntry[]>([]);
const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
const [recAccountCode, setRecAccountCode] = useState('');
const [statementBalance, setStatementBalance] = useState('');
```

### View Architecture

```
┌────────────────────────────────────────────────────────┐
│              Accounting Module Views                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Chart of Accounts (COA)                               │
│  ├── List all ledger accounts                          │
│  ├── Sorted by account code                            │
│  ├── Shows type, category, balance                     │
│  └── Reconciliation status indicator                   │
│                                                        │
│  General Ledger                                        │
│  ├── Journal entry list                                │
│  ├── Filter by date, reference                         │
│  ├── View entry details (debits/credits)               │
│  └── Export functionality                              │
│                                                        │
│  End of Period Operations                              │
│  ├── Daily Accruals button                             │
│  ├── Batch Provisions button                           │
│  └── Processing status display                         │
│                                                        │
│  Reconciliation                                        │
│  ├── Account selector                                  │
│  ├── Statement balance input                           │
│  ├── Run reconciliation                                │
│  └── Variance report                                   │
│                                                        │
│  Audit Trail                                           │
│  ├── All system changes                                │
│  ├── Filter by entity type, user                       │
│  └── Before/after value comparison                     │
└────────────────────────────────────────────────────────┘
```

### Chart of Accounts Structure

```typescript
// Account Types
enum AccountType {
  ASSET = 'ASSET',         // Cash, Loans Receivable
  LIABILITY = 'LIABILITY', // Deposits, Payables
  EQUITY = 'EQUITY',       // Retained Earnings
  INCOME = 'INCOME',       // Interest Income, Fee Income
  EXPENSE = 'EXPENSE'      // Bad Debt Expense, Operating Expenses
}

// Account Categories
type Category = 'BS' | 'PL';  // Balance Sheet or Profit & Loss
```

### Sample Chart of Accounts

| Code | Name | Type | Category |
|------|------|------|----------|
| 1000 | Cash and Cash Equivalents | ASSET | BS |
| 1100 | Loans Receivable | ASSET | BS |
| 1110 | Allowance for Loan Losses | ASSET | BS (contra) |
| 2000 | Accounts Payable | LIABILITY | BS |
| 3000 | Retained Earnings | EQUITY | BS |
| 4000 | Interest Income | INCOME | PL |
| 4100 | Fee Income | INCOME | PL |
| 5000 | Bad Debt Expense | EXPENSE | PL |
| 5100 | Operating Expenses | EXPENSE | PL |

### Journal Entry Structure

```typescript
interface JournalEntry {
  id: string;
  date: string;
  description: string;
  referenceId: string;  // Links to loan/transaction
  lines: JournalLine[];
  createdBy: string;
  createdAt: string;
}

interface JournalLine {
  accountCode: string;
  accountName: string;
  debit: number;
  credit: number;
}

// Double-entry rule: Sum of debits = Sum of credits
```

### Example: Disbursement Journal Entry

```
Loan Disbursement: $10,000

Dr. Loans Receivable          $10,000
    Cr. Cash                            $10,000

Journal Entry:
{
  id: 'je_001',
  description: 'Loan Disbursement - LN-2024-001',
  referenceId: 'loan_123',
  lines: [
    { accountCode: '1100', accountName: 'Loans Receivable', debit: 10000, credit: 0 },
    { accountCode: '1000', accountName: 'Cash', debit: 0, credit: 10000 }
  ]
}
```

### Period-End Operations

#### Daily Accruals

```typescript
const handleAccruals = async () => {
  setProcessing(true);
  const amount = await runDailyAccruals();
  await refreshData();
  setProcessing(false);
  alert(`Daily Accruals Completed. Booked $${amount} to Interest Income.`);
};

// Behind the scenes:
// For each active loan:
//   Daily Interest = (Principal × Rate) / 365
//   Dr. Interest Receivable
//   Cr. Interest Income
```

#### Batch Provisions (IFRS 9)

```typescript
const handleProvisions = async () => {
  setProcessing(true);
  const amount = await runBatchProvisions();
  await refreshData();
  setProcessing(false);
  alert(`Batch Provisioning Completed. Booked $${amount} to Bad Debt Expense.`);
};

// Behind the scenes:
// Based on PAR bucket:
//   Current (0-30):    1% provision
//   PAR 30-60:        10% provision
//   PAR 61-90:        50% provision
//   PAR 90+:         100% provision
//
// Dr. Bad Debt Expense
// Cr. Allowance for Loan Losses
```

### Bank Reconciliation

```typescript
const handleReconcile = async () => {
  if (!recAccountCode) return;
  
  setProcessing(true);
  await reconcileAccount(recAccountCode);
  await refreshData();
  setProcessing(false);
  
  alert('Account reconciled successfully!');
  setStatementBalance('');
};

// Process:
// 1. Get ledger balance for account
// 2. Compare with statement balance
// 3. Identify reconciling items
// 4. Create adjusting entries if needed
// 5. Mark account as reconciled with date
```

---

## ReportsCenter.tsx - Report Generation

### Purpose
Centralized report generation hub with 18+ report types and permission-based access.

### State Management

```typescript
const [activeReport, setActiveReport] = useState<ReportType>('disbursement-register');
const [reportData, setReportData] = useState<any>(null);
const [loading, setLoading] = useState(true);
const [dateRange, setDateRange] = useState<{ start: string; end: string }>({
  start: oneMonthAgo,
  end: today
});
```

### Report Permission Matrix

```typescript
const reportPermissions: Record<ReportType, Permission> = {
  'disbursement-register': 'GENERATE_DISBURSEMENT_REPORT',
  'active-loan-portfolio': 'GENERATE_ACTIVE_LOAN_REPORT',
  'aging-par-report': 'GENERATE_AGING_PAR_REPORT',
  'transaction-ledger': 'GENERATE_TRANSACTION_LEDGER',
  'income-statement': 'GENERATE_INCOME_STATEMENT',
  'daily-cash-flow': 'GENERATE_DAILY_CASHFLOW',
  'daily-recovery-manifest': 'GENERATE_DAILY_RECOVERY',
  'expected-collection': 'GENERATE_EXPECTED_COLLECTION',
  'ptp-performance': 'GENERATE_PTP_PERFORMANCE',
  'collector-activity-scorecard': 'GENERATE_COLLECTOR_SCORECARD',
  'bucket-roll-rate': 'GENERATE_ROLL_RATE',
  'legal-handover-list': 'GENERATE_LEGAL_HANDOVER',
  'master-loan-tape': 'GENERATE_LOAN_TAPE',
  'vintage-analysis': 'GENERATE_VINTAGE_ANALYSIS',
  'ifrs9-expected-loss': 'GENERATE_IFRS9',
  'application-funnel': 'GENERATE_APPLICATION_FUNNEL',
  'underwriting-decision': 'GENERATE_UNDERWRITING_DECISION',
  'tat-report': 'GENERATE_TAT_REPORT',
  'agent-performance': 'GENERATE_AGENT_PERFORMANCE',
  'writeoff-register': 'GENERATE_WRITEOFF_REGISTER',
};

const hasPermission = (report: ReportType): boolean => {
  const permission = reportPermissions[report];
  return ROLE_PERMISSIONS[userRole]?.includes(permission) || false;
};
```

### Report Generation Flow

```
User selects report type
        ↓
Permission check (hasPermission)
        ↓
If denied → Show "Access Denied"
If allowed → Continue
        ↓
Set loading state
        ↓
Call appropriate API function
├── getDisbursementRegister(start, end)
├── getActiveLoanPortfolio(start, end)
├── getAgingParReport()
├── getIncomeStatement(start, end)
└── ... etc
        ↓
Receive data
        ↓
Render based on report type
├── Table view
├── Chart view
└── Export options (Excel, PDF)
        ↓
Clear loading state
```

### Report Categories

```
┌─────────────────────────────────────────────────────────┐
│                  Report Categories                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Operational Reports                                    │
│  ├── Disbursement Register                              │
│  ├── Active Loan Portfolio                              │
│  ├── Aging PAR Report                                   │
│  ├── Daily Recovery Manifest                            │
│  ├── Expected Collection                                │
│  └── PTP Performance                                    │
│                                                         │
│  Financial Reports                                      │
│  ├── Transaction Ledger                                 │
│  ├── Income Statement                                   │
│  ├── Daily Cash Flow                                    │
│  └── IFRS 9 Expected Loss                               │
│                                                         │
│  Management Reports                                     │
│  ├── Master Loan Tape                                   │
│  ├── Vintage Analysis                                   │
│  ├── Application Funnel                                 │
│  ├── TAT Report                                         │
│  ├── Agent Performance                                  │
│  ├── Collector Scorecard                                │
│  ├── Bucket Roll Rate                                   │
│  ├── Legal Handover List                                │
│  ├── Underwriting Decision                              │
│  └── Write-off Register                                 │
└─────────────────────────────────────────────────────────┘
```

### Sample Report: Aging PAR Report

```typescript
const getAgingParReport = async () => {
  const response = await apiClient.get('/reports/aging-par-report');
  return response.data.data;
};

// Expected data structure:
[
  { bucket: 'Current (0-30 days)', count: 45, totalOutstanding: 450000 },
  { bucket: 'PAR 30-60', count: 12, totalOutstanding: 120000 },
  { bucket: 'PAR 61-90', count: 5, totalOutstanding: 50000 },
  { bucket: 'PAR 90+', count: 3, totalOutstanding: 30000 }
]

// Render as table or bar chart
```

### Export Functionality

```typescript
const handleExport = (format: 'excel' | 'pdf' | 'csv') => {
  switch (format) {
    case 'excel':
      const ws = XLSX.utils.json_to_sheet(reportData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Report');
      XLSX.writeFile(wb, `${activeReport}-${dateRange.start}.xlsx`);
      break;
    case 'csv':
      // CSV export logic
      break;
    case 'pdf':
      // PDF export logic (using react-pdf or similar)
      break;
  }
};
```

---

## Component Communication Patterns

### Parent → Child (Props)

```typescript
// App.tsx passes data to child components
<ClientPWA
  clientId={currentUser.id}
  clientName={currentUser.name}
  onLogout={handleLogout}
/>
```

### Child → Parent (Callbacks)

```typescript
// Child component calls parent callback
const handleApply = async () => {
  await submitLoanApplication(data);
  showNotification('Success!', 'success');
  setTimeout(() => setView('dashboard'), 2000);  // Navigate via parent
};
```

### Sibling Communication (via Common Parent)

```
AdminDashboard (parent)
├── ProductsView
└── UserManagement

// Shared state lifted to AdminDashboard
const [products, setProducts] = useState([]);

// Both children receive setProducts via props
```

### Global State (Mock DB / API)

```typescript
// Any component can call shared services
const loans = await getLoans();
const client = await getClient(id);
await makeRepayment(loanId, amount);
```

---

## Styling Approach

### Utility-First (Tailwind-like)

```tsx
<div className="min-h-screen bg-slate-50">
  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
    <h2 className="text-xl font-bold text-slate-800">Title</h2>
  </div>
</div>
```

### Custom Animations

```typescript
const styles = `
@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.animate-slide-in-right {
  animation: slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
`;

// Applied via <style>{styles}</style> in component
```

### Conditional Styling

```tsx
<span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase border 
  ${status === 'ACTIVE' 
    ? 'bg-green-50 text-green-700 border-green-200' 
    : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
  {status}
</span>
```

---

## Error Handling Patterns

### Try-Catch with User Feedback

```typescript
const handlePayment = async (e: React.FormEvent) => {
  e.preventDefault();
  setIsSubmitting(true);
  
  try {
    await makeRepayment(selectedLoanId, payAmount);
    showNotification('Payment processed successfully', 'success');
    setTimeout(() => setView('dashboard'), 2000);
  } catch (error) {
    showNotification('Payment failed: ' + error, 'error');
  } finally {
    setIsSubmitting(false);
  }
};
```

### Loading States

```typescript
const [loading, setLoading] = useState(true);

{loading ? (
  <div className="p-8 text-center">Loading...</div>
) : (
  <DataTable data={data} />
)}
```

### Validation

```typescript
const handleSave = () => {
  if (!editProduct.name) return;
  if (!editProduct.interestRate) return;
  // ... validation
  
  saveProduct(editProduct);
};
```

---

## Summary

The IntZam LMS components follow these key patterns:

1. **Single Responsibility**: Each component handles one domain (e.g., Collections, Accounting)
2. **State Colocation**: State is kept as close as possible to where it's used
3. **Composition**: Complex UIs built from smaller, reusable components
4. **Type Safety**: TypeScript interfaces define data contracts
5. **Permission-Based Rendering**: UI elements shown/hidden based on user role
6. **Optimistic Updates**: UI updates immediately, syncs with backend asynchronously
7. **Responsive Design**: Mobile-first approach, especially for Client PWA
8. **Accessibility**: Semantic HTML, proper labels, keyboard navigation

---

*Component documentation for IntZam LMS v0.0.0*
