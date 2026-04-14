# IntZam LMS - Patterns & Conventions

This document details the shared patterns, conventions, and best practices used throughout the IntZam LMS codebase.

---

## Table of Contents

1. [Component Communication Patterns](#component-communication-patterns)
2. [State Management Patterns](#state-management-patterns)
3. [Styling Approach](#styling-approach)
4. [Error Handling Patterns](#error-handling-patterns)
5. [Loading State Patterns](#loading-state-patterns)
6. [Form Handling Patterns](#form-handling-patterns)
7. [Permission & Access Control](#permission--access-control)
8. [Data Flow Architecture](#data-flow-architecture)
9. [Code Organization](#code-organization)
10. [Naming Conventions](#naming-conventions)

---

## Component Communication Patterns

### 1. Parent → Child Communication (Props)

**Pattern:** Data flows downward through props

```tsx
// Parent (App.tsx)
<ClientPWA
  clientId={currentUser.id}
  clientName={currentUser.name}
  onLogout={handleLogout}
/>

// Child (ClientPWA.tsx)
interface ClientPWAProps {
  clientId: string;
  clientName: string;
  onLogout: () => void;
}

export const ClientPWA: React.FC<ClientPWAProps> = ({ clientId, clientName, onLogout }) => {
  // Use props directly
  useEffect(() => {
    loadData(clientId);
  }, [clientId]);
};
```

**Best Practices:**
- Use TypeScript interfaces for prop type safety
- Destructure props in function signature for clarity
- Keep prop interfaces small and focused
- Use descriptive prop names

---

### 2. Child → Parent Communication (Callback Props)

**Pattern:** Events bubble upward through callback functions

```tsx
// Child Component (LandingPage.tsx)
interface LandingPageProps {
  onLoginClient: (client: Client) => void;
  onLoginStaff: (role: UserRole) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLoginClient, onLoginStaff }) => {
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // ... authentication logic
    
    if (client) {
      onLoginClient(client);  // Notify parent
    }
  };
};

// Parent Component (App.tsx)
const handleClientLogin = (client: Client) => {
  setCurrentUser(client);
  setActiveView('client');
};

<LandingPage
  onLoginClient={handleClientLogin}
  onLoginStaff={handleStaffLogin}
/>
```

**Best Practices:**
- Name callbacks with `on` prefix (e.g., `onLogin`, `onSubmit`)
- Pass data as parameters to callbacks
- Keep callback logic in parent, not child
- Document expected parameters in interface

---

### 3. Sibling Communication (Via Common Parent)

**Pattern:** Siblings communicate through lifted state in parent

```tsx
// Parent (AdminDashboard.tsx)
const [products, setProducts] = useState<LoanProduct[]>([]);

const refreshProducts = async () => {
  const p = await getProducts();
  setProducts(p);
};

// Both children receive the same data/updater
<ProductsView products={products} setProducts={setProducts} />
<UserManagement refreshTrigger={refreshProducts} />
```

**Alternative: Event Bus Pattern (for distant components)**

```tsx
// Custom event emitter (services/eventBus.ts)
export const eventBus = {
  emit: (event: string, data?: any) => { /* ... */ },
  on: (event: string, callback: (data?: any) => void) => { /* ... */ }
};

// Component A emits
eventBus.emit('loan-updated', loanId);

// Component B listens
useEffect(() => {
  const unsubscribe = eventBus.on('loan-updated', (id) => {
    if (id === selectedLoanId) refresh();
  });
  return unsubscribe;
}, []);
```

---

### 4. Global State (Shared Services)

**Pattern:** Shared data accessed via service layer

```tsx
// Any component can call
const loans = await getLoans();
const client = await getClient(id);
await makeRepayment(loanId, amount);

// Service abstracts data source (mock vs real API)
// services/apiDataLayer.ts
export const getLoans = async (params) => {
  if (USE_MOCK_DATA && mockDb) {
    return mockDb.getLoans(params);
  }
  try {
    const response = await apiClient.get('/loans', { params });
    return response.data;
  } catch (error) {
    // Fallback to mock
    return mockDb.getLoans(params);
  }
};
```

---

### 5. Context API (For Deep Trees)

**Pattern:** Avoid prop drilling with React Context

```tsx
// Create context
const AuthContext = createContext<AuthContextType | null>(null);

// Provider at root
<AuthContext.Provider value={{ user, login, logout }}>
  <App />
</AuthContext.Provider>

// Consume in deeply nested component
const { user, logout } = useContext(AuthContext);
```

**When to Use:**
- Theme/configuration shared across app
- Authentication state
- User preferences
- Data needed by many nested components

**When NOT to Use:**
- Data only needed by direct parent/child
- Frequently changing data (causes re-renders)
- When props are sufficient

---

## State Management Patterns

### 1. Component-Level State (useState)

**Pattern:** Local state for component-specific data

```tsx
const [view, setView] = useState<'dashboard' | 'apply' | 'pay'>('dashboard');
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
```

**Best Practices:**
- Keep state as close to usage as possible
- Split related state into multiple useState calls
- Use descriptive variable names
- Initialize with sensible defaults

---

### 2. Derived State

**Pattern:** Calculate values from existing state/props

```tsx
// Bad: Storing derived value in state
const [total, setTotal] = useState(0);
const [items, setItems] = useState([]);

// Good: Calculate from existing state
const total = items.reduce((sum, item) => sum + item.amount, 0);
```

**When to Derive:**
- Value can be calculated from other state
- Value is used for display only
- No user interaction modifies it directly

---

### 3. State Initialization from Props

**Pattern:** Initialize state from props with default

```tsx
interface Props {
  initialAmount?: number;
}

const LoanForm: React.FC<Props> = ({ initialAmount = 1000 }) => {
  const [amount, setAmount] = useState(initialAmount);
  // ...
};
```

**Caution:** Avoid syncing state with props after initial render unless intentional

---

### 4. Batch State Updates

**Pattern:** React 18 automatically batches state updates

```tsx
// Both updates batched in React 18+
setLoading(true);
setError(null);

// In async callbacks, use functional updates
setData(newData);
setLoading(false);  // May not batch if in async callback
```

---

### 5. State Reset Pattern

**Pattern:** Reset multiple states at once

```tsx
const initialState = {
  view: 'dashboard',
  selectedLoan: null,
  paymentAmount: 0,
  isSettlement: false
};

const [state, setState] = useState(initialState);

const handleLogout = () => {
  setState(initialState);  // Reset all
};
```

---

## Styling Approach

### 1. Utility-First CSS (Tailwind-like)

**Pattern:** Compose styles using small utility classes

```tsx
<div className="min-h-screen bg-slate-50">
  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
    <h2 className="text-xl font-bold text-slate-800">Title</h2>
    <p className="text-slate-500 text-sm mt-2">Description</p>
  </div>
</div>
```

**Benefits:**
- No CSS files to maintain
- Consistent spacing/sizing scale
- Easy to modify inline
- Smaller bundle size (no unused CSS)

---

### 2. Conditional Styling

**Pattern:** Apply classes based on state/props

```tsx
// Ternary for binary conditions
<button className={`px-4 py-2 rounded ${isActive ? 'bg-blue-500' : 'bg-gray-200'}`}>
  Click Me
</button>

// Template literal for multiple conditions
<div className={`
  p-4 rounded-lg border
  ${isSelected ? 'bg-indigo-50 border-indigo-500' : 'bg-white border-slate-200'}
  ${isError ? 'border-red-500' : ''}
  ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
`}>
  Content
</div>
```

**Helper Function Pattern:**

```tsx
const classNames = (...classes: (string | undefined | null | false)[]) => {
  return classes.filter(Boolean).join(' ');
};

// Usage
<div className={classNames(
  'base-class',
  isActive && 'active-class',
  isError && 'error-class'
)}>
```

---

### 3. Custom Animations

**Pattern:** Define animations as template strings

```tsx
// Animation styles
const styles = `
@keyframes slideInRight {
  from { 
    transform: translateX(100%); 
    opacity: 0; 
  }
  to { 
    transform: translateX(0); 
    opacity: 1; 
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-slide-in-right {
  animation: slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}

.animate-pulse {
  animation: pulse 2s infinite;
}
`;

// Apply in component
function App() {
  return (
    <>
      <style>{styles}</style>
      <div className="animate-slide-in-right">
        {/* Content */}
      </div>
    </>
  );
}
```

**Animation Timing Functions:**

| Name | Cubic Bezier | Use Case |
|------|--------------|----------|
| Linear | `linear` | Mechanical, robotic |
| Ease | `ease` | Natural, smooth |
| Ease Out | `cubic-bezier(0, 0, 0.2, 1)` | Enter animations |
| Ease In | `cubic-bezier(0.4, 0, 1, 1)` | Exit animations |
| Custom | `cubic-bezier(0.16, 1, 0.3, 1)` | Snappy, modern |

---

### 4. Responsive Design

**Pattern:** Mobile-first with breakpoint prefixes

```tsx
<div className="
  grid 
  grid-cols-1        /* Mobile: 1 column */
  md:grid-cols-2     /* Tablet: 2 columns */
  lg:grid-cols-3     /* Desktop: 3 columns */
  gap-4
">
  {/* Content */}
</div>
```

**Breakpoint Conventions:**

| Prefix | Min Width | Target |
|--------|-----------|--------|
| (none) | 0px | Mobile |
| sm | 640px | Small tablets |
| md | 768px | Tablets |
| lg | 1024px | Laptops |
| xl | 1280px | Desktops |
| 2xl | 1536px | Large screens |

---

### 5. Component-Specific Style Objects

**Pattern:** Extract complex styles to constants

```tsx
const cardStyles = {
  base: 'bg-white p-6 rounded-xl border border-slate-200 shadow-sm',
  interactive: 'hover:border-indigo-300 transition-colors cursor-pointer',
  disabled: 'opacity-50 cursor-not-allowed bg-slate-100'
};

function ProductCard() {
  return (
    <div className={`${cardStyles.base} ${cardStyles.interactive}`}>
      {/* Content */}
    </div>
  );
}
```

---

## Error Handling Patterns

### 1. Try-Catch with User Feedback

**Pattern:** Catch errors and display to user

```tsx
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

**Key Elements:**
- Set loading state before async operation
- Show success message on completion
- Show error message on failure
- Clear loading state in finally block

---

### 2. Error State Component

**Pattern:** Dedicated error display component

```tsx
interface ErrorDisplayProps {
  error: string | null;
  onDismiss: () => void;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error, onDismiss }) => {
  if (!error) return null;
  
  return (
    <div className="p-3 bg-red-50 border border-red-100 rounded-lg flex items-center gap-2 text-red-600">
      <AlertCircle className="h-4 w-4" />
      <span>{error}</span>
      <button onClick={onDismiss} className="ml-auto">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
};

// Usage
const [error, setError] = useState<string | null>(null);

<ErrorDisplay error={error} onDismiss={() => setError(null)} />
```

---

### 3. Error Boundary (Class Component)

**Pattern:** Catch React rendering errors

```tsx
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Reload Application
          </button>
        </div>
      );
    }
    
    return this.props.children;
  }
}

// Wrap app
<ErrorBoundary>
  <App />
</ErrorBoundary>
```

---

### 4. API Error Handling with Fallback

**Pattern:** Graceful degradation when API fails

```tsx
export const getLoans = async (params) => {
  // Try real API first
  try {
    const response = await apiClient.get('/loans', { params });
    return response.data;
  } catch (error) {
    console.error('API failed, falling back to mock:', error);
    
    // Fallback to mock data
    if (mockDb) {
      return mockDb.getLoans(params);
    }
    
    // Last resort: return empty data
    return { data: [], pagination: { total: 0 } };
  }
};
```

---

### 5. Validation Errors

**Pattern:** Collect and display form validation errors

```tsx
const [errors, setErrors] = useState<Record<string, string>>({});

const validateForm = () => {
  const newErrors: Record<string, string> = {};
  
  if (!formData.amount) {
    newErrors.amount = 'Amount is required';
  } else if (formData.amount < 100) {
    newErrors.amount = 'Minimum amount is $100';
  }
  
  if (!formData.term) {
    newErrors.term = 'Term is required';
  }
  
  setErrors(newErrors);
  return Object.keys(newErrors).length === 0;
};

const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  if (validateForm()) {
    // Submit form
  }
};

// Display error
<input
  className={`border ${errors.amount ? 'border-red-500' : 'border-slate-300'}`}
  value={formData.amount}
  onChange={...}
/>
{errors.amount && (
  <p className="text-red-500 text-xs mt-1">{errors.amount}</p>
)}
```

---

## Loading State Patterns

### 1. Simple Loading Flag

**Pattern:** Boolean flag for loading state

```tsx
const [loading, setLoading] = useState(false);

const fetchData = async () => {
  setLoading(true);
  try {
    const data = await api.getData();
    setData(data);
  } finally {
    setLoading(false);
  }
};

{loading ? (
  <div className="p-8 text-center text-slate-500">Loading...</div>
) : (
  <DataTable data={data} />
)}
```

---

### 2. Loading Spinner Component

**Pattern:** Reusable spinner component

```tsx
const LoadingSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({ size = 'md' }) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  };
  
  return (
    <div className="flex items-center justify-center">
      <div className={`animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600 ${sizeClasses[size]}`} />
    </div>
  );
};

// Usage
{loading && <LoadingSpinner size="lg" />}
```

---

### 3. Skeleton Loading

**Pattern:** Show placeholder while content loads

```tsx
const SkeletonCard = () => (
  <div className="bg-white p-6 rounded-xl border border-slate-200 animate-pulse">
    <div className="h-4 bg-slate-200 rounded w-3/4 mb-4"></div>
    <div className="h-3 bg-slate-200 rounded w-1/2 mb-2"></div>
    <div className="h-3 bg-slate-200 rounded w-2/3"></div>
  </div>
);

// Usage
{loading ? (
  <div className="space-y-4">
    {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
  </div>
) : (
  <DataList data={data} />
)}
```

---

### 4. Per-Action Loading States

**Pattern:** Track loading state for individual actions

```tsx
const [submitting, setSubmitting] = useState(false);
const [deleting, setDeleting] = useState(false);
const [exporting, setExporting] = useState(false);

<button disabled={submitting} onClick={handleSubmit}>
  {submitting ? 'Submitting...' : 'Submit'}
</button>

<button disabled={deleting} onClick={handleDelete}>
  {deleting ? 'Deleting...' : 'Delete'}
</button>
```

---

### 5. Optimistic Updates

**Pattern:** Update UI immediately, revert on error

```tsx
const handleToggle = async (id: string) => {
  const previousState = items.find(i => i.id === id)?.active;
  
  // Optimistic update
  setItems(items.map(item => 
    item.id === id ? { ...item, active: !item.active } : item
  ));
  
  try {
    await api.toggleItem(id);
  } catch (error) {
    // Revert on error
    setItems(items.map(item => 
      item.id === id ? { ...item, active: previousState } : item
    ));
    showNotification('Failed to update', 'error');
  }
};
```

---

## Form Handling Patterns

### 1. Controlled Components

**Pattern:** Form data controlled by React state

```tsx
const [formData, setFormData] = useState({
  name: '',
  email: '',
  phone: ''
});

const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setFormData({
    ...formData,
    [e.target.name]: e.target.value
  });
};

<form onSubmit={handleSubmit}>
  <input
    name="name"
    value={formData.name}
    onChange={handleChange}
  />
  <input
    name="email"
    type="email"
    value={formData.email}
    onChange={handleChange}
  />
</form>
```

---

### 2. Form State Reset

**Pattern:** Reset form after submission

```tsx
const initialFormState = {
  name: '',
  email: '',
  phone: ''
};

const [formData, setFormData] = useState(initialFormState);

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  await submitForm(formData);
  setFormData(initialFormState);  // Reset
};
```

---

### 3. Multi-Step Forms

**Pattern:** Break complex forms into steps

```tsx
const [step, setStep] = useState(1);
const [formData, setFormData] = useState({
  // Step 1
  name: '',
  email: '',
  // Step 2
  address: '',
  city: '',
  // Step 3
  terms: false
});

const nextStep = () => {
  if (validateStep(step)) {
    setStep(step + 1);
  }
};

const prevStep = () => setStep(step - 1);

{step === 1 && <Step1 data={formData} onChange={setFormData} />}
{step === 2 && <Step2 data={formData} onChange={setFormData} />}
{step === 3 && <Step3 data={formData} onChange={setFormData} />}

<div className="flex gap-2">
  {step > 1 && <button onClick={prevStep}>Back</button>}
  {step < 3 ? (
    <button onClick={nextStep}>Next</button>
  ) : (
    <button onClick={handleSubmit}>Submit</button>
  )}
</div>
```

---

### 4. File Upload Simulation

**Pattern:** Simulate file upload with timeout

```tsx
const [uploadedDocs, setUploadedDocs] = useState<Record<string, boolean>>({});
const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);

const simulateUpload = (docName: string) => {
  setUploadingDoc(docName);
  setTimeout(() => {
    setUploadedDocs(prev => ({ ...prev, [docName]: true }));
    setUploadingDoc(null);
  }, 1500);
};

// Render
{requiredDocs.map(doc => (
  <div
    key={doc}
    onClick={() => simulateUpload(doc)}
    className={uploadedDocs[doc] ? 'uploaded' : 'pending'}
  >
    {uploadingDoc === doc ? (
      <Spinner />
    ) : uploadedDocs[doc] ? (
      <CheckIcon />
    ) : (
      <UploadIcon />
    )}
    {doc}
  </div>
))}
```

---

## Permission & Access Control

### 1. Role-Based Permission Check

**Pattern:** Check if user role has permission

```tsx
const hasPermission = (permission: Permission): boolean => {
  return ROLE_PERMISSIONS[userRole]?.includes(permission) || false;
};

// Usage in component
{hasPermission('APPROVE_LOAN') && (
  <button onClick={handleApprove}>Approve Loan</button>
)}
```

---

### 2. Permission-Gated Routes

**Pattern:** Restrict access to entire views

```tsx
const ReportsCenter: React.FC<{ userRole: UserRole }> = ({ userRole }) => {
  const reportPermissions: Record<ReportType, Permission> = {
    'disbursement-register': 'GENERATE_DISBURSEMENT_REPORT',
    'income-statement': 'GENERATE_INCOME_STATEMENT',
    // ...
  };
  
  const hasPermission = (report: ReportType): boolean => {
    const permission = reportPermissions[report];
    return ROLE_PERMISSIONS[userRole]?.includes(permission) || false;
  };
  
  return (
    <div>
      {hasPermission('disbursement-register') ? (
        <ReportView type="disbursement-register" />
      ) : (
        <AccessDenied message="You don't have permission to view this report" />
      )}
    </div>
  );
};
```

---

### 3. Permission-Based UI Rendering

**Pattern:** Hide/show UI elements based on permissions

```tsx
<div className="action-buttons">
  {hasPermission('APPROVE_LOAN') && (
    <button className="approve-btn">Approve</button>
  )}
  {hasPermission('REJECT_LOAN') && (
    <button className="reject-btn">Reject</button>
  )}
  {hasPermission('WRITE_OFF_LOAN') && (
    <button className="writeoff-btn">Write Off</button>
  )}
</div>
```

---

### 4. Role Display Helper

**Pattern:** Format role names for display

```tsx
const formatRoleName = (role: UserRole): string => {
  return role
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ');
};

// Usage
<span className="role-badge">{formatRoleName(userRole)}</span>
// "PORTFOLIO_MANAGER" → "Portfolio Manager"
```

---

## Data Flow Architecture

### 1. Unidirectional Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    User Interaction                      │
│                    (click, submit)                       │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Event Handler                         │
│              (handleLogin, handleSubmit)                 │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    State Update                          │
│              (setState, dispatch)                        │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Component Re-render                   │
│              (UI reflects new state)                     │
└─────────────────────────────────────────────────────────┘
```

---

### 2. API Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Component                             │
│              (AdminDashboard, ClientPWA)                 │
└───────────────────────────┬─────────────────────────────┘
                            │ calls
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Service Layer                           │
│            (apiDataLayer.ts, mockDb.ts)                  │
│                                                          │
│  • Checks USE_MOCK_DATA flag                             │
│  • Routes to mock or real API                            │
│  • Handles errors and fallbacks                          │
└─────────┬─────────────────────────────────┬─────────────┘
          │                                 │
          │ Mock Mode                       │ Production
          ▼                                 ▼
┌──────────────────┐            ┌──────────────────────────┐
│    mockDb.ts     │            │   apiClient (axios)      │
│  (in-memory DB)  │            │   HTTP requests          │
└──────────────────┘            └───────────┬──────────────┘
                                            │
                                            ▼
                                  ┌──────────────────────────┐
                                  │   Express Backend        │
                                  │   (server.ts)            │
                                  └───────────┬──────────────┘
                                              │
                                              ▼
                                  ┌──────────────────────────┐
                                  │   Prisma ORM             │
                                  └───────────┬──────────────┘
                                              │
                                              ▼
                                  ┌──────────────────────────┐
                                  │   Database (SQLite/PG)   │
                                  └──────────────────────────┘
```

---

### 3. State Synchronization

```tsx
// Load data on mount
useEffect(() => {
  const loadData = async () => {
    const [loans, products, clients] = await Promise.all([
      getLoans(),
      getProducts(),
      getClients()
    ]);
    setLoans(loans);
    setProducts(products);
    setClients(clients);
  };
  loadData();
}, []);

// Refresh on action
const handleApprove = async () => {
  await updateLoanStatus(id, 'APPROVED');
  await refreshLoans();  // Re-fetch to get updated data
};
```

---

## Code Organization

### 1. File Structure

```
intzam/
├── components/
│   ├── AdminDashboard.tsx      # ~900 lines, multiple sub-components
│   ├── ClientPWA.tsx           # ~950 lines, multiple views
│   ├── LandingPage.tsx         # ~500 lines, login + register
│   ├── Underwriting.tsx        # Loan approval module
│   ├── LoanServicing.tsx       # Active loan management
│   ├── Collections.tsx         # Debt collection module
│   ├── Accounting.tsx          # Financial accounting
│   └── ReportsCenter.tsx       # Report generation hub
├── services/
│   ├── apiDataLayer.ts         # API abstraction (switches mock/real)
│   ├── mockDb.ts               # In-memory database (~1800 lines)
│   ├── interestCalculationService.ts  # Loan calculations
│   ├── geminiService.ts        # AI integration
│   └── creditApiService.ts     # External credit bureau
├── prisma/
│   ├── schema.prisma           # Database schema
│   └── seed.js                 # Test data
├── types.ts                    # TypeScript definitions (~400 lines)
├── App.tsx                     # Root component
├── server.ts                   # Express backend
└── vite.config.ts              # Build configuration
```

---

### 2. Component Internal Structure

```tsx
// 1. Imports
import React, { useState, useEffect } from 'react';
import { Icon1, Icon2 } from 'lucide-react';
import { Type1, Type2 } from '../types';
import { service1, service2 } from '../services';

// 2. Interfaces
interface ComponentProps {
  prop1: string;
  prop2: number;
}

// 3. Sub-components (if any)
const SubComponent = ({ data }) => { ... };

// 4. Main Component
export const MainComponent: React.FC<ComponentProps> = ({ prop1, prop2 }) => {
  // 4a. State declarations
  const [state1, setState1] = useState(...);
  
  // 4b. useEffect hooks
  useEffect(() => { ... }, []);
  
  // 4c. Event handlers
  const handleClick = () => { ... };
  
  // 4d. Helper functions
  const formatData = (data) => { ... };
  
  // 4e. Render
  return (
    <div>...</div>
  );
};
```

---

### 3. Type Definitions Organization

```typescript
// types.ts

// 1. Enums first
export enum LoanStatus { ... }
export enum UserRole { ... }
export enum ClientTier { ... }

// 2. Permission types
export type Permission = 'VIEW_DASHBOARD' | ...;

// 3. Permission mappings
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = { ... };

// 4. Interface definitions
export interface Client { ... }
export interface LoanApplication { ... }
export interface LoanProduct { ... }

// 5. Helper types
export interface TierConfig { ... }
export interface PayoffQuote { ... }
```

---

## Naming Conventions

### 1. Component Names

```tsx
// PascalCase for components
export const AdminDashboard: React.FC = () => { ... };
export const ClientPWA: React.FC = () => { ... };

// File names match component names
AdminDashboard.tsx
ClientPWA.tsx
```

---

### 2. Variable Names

```tsx
// camelCase for variables and functions
const currentUser = useState(null);
const handleLogin = () => { ... };
const isLoading = useState(false);

// Boolean prefixes
const isActive = ...;
const hasPermission = ...;
const canSubmit = ...;
const shouldRender = ...;
```

---

### 3. State Variables

```tsx
// Descriptive names
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [selectedLoan, setSelectedLoan] = useState(null);

// Collection state
const [loans, setLoans] = useState([]);
const [products, setProducts] = useState([]);

// Form state
const [formData, setFormData] = useState({ ... });
const [errors, setErrors] = useState({ ... });
```

---

### 4. Event Handlers

```tsx
// Prefix with action
const handleSubmit = (e) => { ... };
const handleClick = (e) => { ... };
const handleChange = (e) => { ... };
const handleLogout = () => { ... };

// Callback props
const onLogin = (user) => { ... };
const onSubmit = (data) => { ... };
const onError = (error) => { ... };
```

---

### 5. Constants

```tsx
// UPPER_SNAKE_CASE for true constants
const MAX_LOAN_AMOUNT = 100000;
const DEFAULT_INTEREST_RATE = 25;

// PascalCase for enums
enum LoanStatus {
  PENDING_APPROVAL = 'PENDING_APPROVAL',
  APPROVED = 'APPROVED',
  ...
}
```

---

## Summary

The IntZam LMS codebase follows these key patterns:

| Category | Pattern | Purpose |
|----------|---------|---------|
| Communication | Props down, events up | Clear data flow |
| State | Local useState | Simple, focused state |
| Styling | Utility-first CSS | No CSS files, consistent design |
| Errors | Try-catch with feedback | User-friendly error handling |
| Loading | Boolean flags + spinners | Clear loading states |
| Forms | Controlled components | Predictable form behavior |
| Permissions | Role-based checks | Secure access control |
| Data | Unidirectional flow | Predictable updates |
| Organization | By feature | Easy to navigate |
| Naming | Descriptive, consistent | Readable code |

---

*Patterns & Conventions documentation for IntZam LMS v0.0.0*
