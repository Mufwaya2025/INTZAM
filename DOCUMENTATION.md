# IntZam LMS - Comprehensive Documentation

## Table of Contents

1. [Overview](#overview)
2. [Project Architecture](#project-architecture)
3. [Technology Stack](#technology-stack)
4. [Core Features](#core-features)
5. [Database Schema](#database-schema)
6. [User Roles & Permissions](#user-roles--permissions)
7. [Loan Products & Configuration](#loan-products--configuration)
8. [Client Features](#client-features)
9. [Admin Dashboard Features](#admin-dashboard-features)
10. [API Reference](#api-reference)
11. [Services Layer](#services-layer)
12. [Reports System](#reports-system)
13. [Development & Deployment](#development--deployment)

---

## Overview

**IntZam LMS** is a comprehensive Loan Management System designed for IntZam Micro Fin Limited. It provides a complete end-to-end solution for microfinance operations, combining traditional lending workflows with modern AI-powered risk assessment.

### Key Capabilities

- **Client Self-Service Portal**: Mobile-first PWA for loan applications, repayments, and account management
- **Staff Dashboard**: Role-based admin panel for loan processing, collections, and reporting
- **AI-Powered Underwriting**: Gemini AI integration for automated risk analysis
- **Comprehensive Reporting**: 18+ regulatory and operational reports
- **Loyalty Program**: Tier-based pricing with automatic rate compression for good clients
- **Rollover Feature**: Flexible loan extension with configurable eligibility rules
- **Collections Management**: Full collection workflow with PTP (Promise to Pay) tracking
- **Accounting Integration**: Double-entry bookkeeping with IFRS 9 compliance

---

## Project Architecture

```
intzam/
├── components/          # React UI components
│   ├── AdminDashboard.tsx    # Main admin interface
│   ├── ClientPWA.tsx         # Client mobile interface
│   ├── LandingPage.tsx       # Authentication & registration
│   ├── Underwriting.tsx      # Loan approval workflow
│   ├── LoanServicing.tsx     # Active loan management
│   ├── Collections.tsx       # Debt collection module
│   ├── Accounting.tsx        # Financial accounting
│   └── ReportsCenter.tsx     # Report generation hub
├── services/            # Business logic layer
│   ├── mockDb.ts             # In-memory data store (dev)
│   ├── apiDataLayer.ts       # API abstraction layer
│   ├── apiService.ts         # Direct API calls
│   ├── geminiService.ts      # AI risk analysis
│   ├── interestCalculationService.ts  # Loan calculations
│   └── creditApiService.ts   # External credit bureau
├── prisma/              # Database layer
│   ├── schema.prisma           # ORM schema definition
│   ├── migrations/             # Database migrations
│   └── seed.js                 # Test data seeder
├── server.ts            # Express backend (TypeScript)
├── server.js            # Express backend (JavaScript)
├── types.ts             # TypeScript type definitions
├── App.tsx              # Root React component
├── vite.config.ts       # Vite bundler configuration
└── tsconfig.json        # TypeScript configuration
```

### Architecture Pattern

The application follows a **hybrid architecture**:

1. **Frontend**: React 19 with TypeScript, using Vite as the build tool
2. **Backend**: Express.js server with Prisma ORM
3. **Database**: SQLite (development) with production-ready schema for PostgreSQL
4. **State Management**: Component-level state with mock data layer for development
5. **API Layer**: Dual-mode operation (mock data in dev, real API in production)

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.2.1 | UI framework |
| TypeScript | 5.8.2 | Type safety |
| Vite | 6.2.0 | Build tool & dev server |
| Lucide React | 0.555.0 | Icon library |
| React Markdown | 10.1.0 | AI response rendering |
| Recharts | 3.5.1 | Data visualization |
| XLSX | 0.18.5 | Excel export |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Express | 5.2.1 | Web framework |
| Prisma | 4.16.2 | Database ORM |
| SQLite | - | Development database |
| Helmet | 8.1.0 | Security headers |
| CORS | 2.8.5 | Cross-origin requests |
| Morgan | 1.10.1 | HTTP logging |
| JWT | 9.0.3 | Authentication tokens |
| Bcrypt | 6.0.0 | Password hashing |
| Joi | 18.0.2 | Schema validation |
| Multer | 2.0.2 | File uploads |

### AI & External Services

| Service | Purpose |
|---------|---------|
| Google Gemini AI (2.5 Flash) | Loan risk analysis |
| External Credit APIs | Credit score verification |

---

## Core Features

### 1. Loan Lifecycle Management

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  PENDING    │───▶│  APPROVED   │───▶│   ACTIVE    │
│  APPROVAL   │    │             │    │             │
└─────────────┘    └─────────────┘    └──────┬──────┘
       ▲                                      │
       │                                      ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  WRITTEN    │◀───│   OVERDUE   │◀───│   CLOSED    │
│    OFF      │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 2. Client Loyalty Tiers

| Tier | Interest Rate | Limit Multiplier | Requirements |
|------|---------------|------------------|--------------|
| BRONZE | 25% (base) | 1.0x | Default |
| SILVER | 20% | 1.3x | 2+ completed loans |
| GOLD | 15% | 1.5x | 5+ completed loans |
| PLATINUM | 12% | 2.0x | 8+ completed loans |

### 3. Rollover System

Clients can extend their loan term by paying a portion of the principal:

- **Configurable per product**: Max rollovers, minimum principal paid %, extension days
- **Fee structure**: Fixed fee + interest component based on extension period
- **Eligibility**: Automatically calculated based on repayment progress

### 4. Early Settlement

- **Payoff quotes**: Real-time calculation of outstanding balance
- **Interest savings**: Automatic computation of saved interest
- **Early termination fees**: Configurable per product

---

## Database Schema

### Core Models

#### Client
```prisma
model Client {
  id                     String    @id @default(cuid())
  userId                 String?   @unique
  name                   String
  email                  String    @unique
  phone                  String    @unique
  nrcNumber              String?   @unique
  kycVerified            Boolean   @default(false)
  creditScore            Int       @default(0)
  monthlyIncome          Float
  employmentStatus       String
  nextOfKinName          String?
  nextOfKinPhone         String?
  nextOfKinRelation      String?
  tier                   String    @default("BRONZE")
  completedLoans         Int       @default(0)
  loans                  Loan[]
  user                   User?
}
```

#### Loan
```prisma
model Loan {
  id              String   @id @default(cuid())
  clientId        String
  productId       String
  loanNumber      String   @unique
  amount          Float
  purpose         String
  termMonths      Int
  interestRate    Float
  status          String   @default("PENDING_APPROVAL")
  documents       String   // JSON array
  repaidAmount    Float    @default(0)
  totalRepayable  Float
  ptpStatus       String?  @default("NONE")
  ptpDate         DateTime?
  ptpAmount       Float?
  rolloverCount   Int      @default(0)
  rolloverDate    DateTime?
  maturityDate    DateTime
  daysOverdue     Int      @default(0)
  client          Client   @relation(fields: [clientId], references: [id])
  product         LoanProduct @relation(fields: [productId], references: [id])
  transactions    Transaction[]
  collectionActivities CollectionActivity[]
}
```

#### LoanProduct
```prisma
model LoanProduct {
  id                        String        @id @default(cuid())
  name                      String
  description               String
  interestType              String        @default("FLAT")
  interestRate              Float
  nominalInterestRate       Float
  creditFacilitationFee     Float
  processingFee             Float
  minAmount                 Float
  maxAmount                 Float
  minTerm                   Int
  maxTerm                   Int
  penaltyRate               Float
  gracePeriodDays           Int
  
  // Rollover Configuration
  rolloverInterestRate            Float
  maxRollovers                    Int      @default(2)
  rolloverMinPrincipalPaidPercent Int      @default(30)
  rolloverExtensionDays           Int
  
  requiredDocuments         String  // JSON array
  tiers                     TierConfig[]
  loans                     Loan[]
}
```

#### TierConfig
```prisma
model TierConfig {
  id                 String      @id @default(cuid())
  productId          String
  tier               String
  interestRate       Float
  maxLimitMultiplier Float
  product            LoanProduct @relation(fields: [productId], references: [id])
  
  @@unique([productId, tier])
}
```

#### Accounting Models
```prisma
model LedgerAccount {
  id            String   @id @default(cuid())
  code          String   @unique
  name          String
  accountType   String   // ASSET, LIABILITY, EQUITY, INCOME, EXPENSE
  category      String   // BS (Balance Sheet) or PL (Profit & Loss)
  balance       Float    @default(0)
  journalLines  JournalLine[]
}

model JournalEntry {
  id          String   @id @default(cuid())
  referenceId String
  description String
  date        DateTime @default(now())
  postedBy    String
  lines       JournalLine[]
}

model JournalLine {
  id          String   @id @default(cuid())
  entryId     String
  accountCode String
  debit       Float    @default(0)
  credit      Float    @default(0)
  entry       JournalEntry @relation(fields: [entryId], references: [id])
  account     LedgerAccount @relation(fields: [accountCode], references: [code])
}
```

---

## User Roles & Permissions

### System Roles

| Role | Key Permissions |
|------|-----------------|
| **ADMIN** | Full system access, staff management, all reports |
| **PORTFOLIO_MANAGER** | View portfolio, post repayments, manage clients |
| **COLLECTIONS_OFFICER** | View collections, contact clients, log activities, PTP management |
| **ACCOUNTANT** | View accounting, generate financial reports, reconciliation |
| **UNDERWRITER** | Approve/reject loans, view underwriting reports, AI analysis |
| **CLIENT** | Apply for loans, make repayments, view own loans |

### Permission Categories

```typescript
// View Permissions
VIEW_DASHBOARD, VIEW_PORTFOLIO, VIEW_COLLECTIONS, 
VIEW_ACCOUNTING, VIEW_CONFIG, VIEW_UNDERWRITING

// Action Permissions
APPROVE_LOAN, REJECT_LOAN, WRITE_OFF_LOAN, POST_REPAYMENT

// Report Permissions (18 types)
GENERATE_DISBURSEMENT_REPORT, GENERATE_ACTIVE_LOAN_REPORT,
GENERATE_AGING_PAR_REPORT, GENERATE_TRANSACTION_LEDGER,
GENERATE_INCOME_STATEMENT, GENERATE_DAILY_CASHFLOW,
GENERATE_DAILY_RECOVERY, GENERATE_EXPECTED_COLLECTION,
GENERATE_PTP_PERFORMANCE, GENERATE_COLLECTOR_SCORECARD,
GENERATE_ROLL_RATE, GENERATE_LEGAL_HANDOVER,
GENERATE_LOAN_TAPE, GENERATE_VINTAGE_ANALYSIS,
GENERATE_IFRS9, GENERATE_APPLICATION_FUNNEL,
GENERATE_UNDERWRITING_DECISION, GENERATE_TAT_REPORT,
GENERATE_AGENT_PERFORMANCE, GENERATE_WRITEOFF_REGISTER

// Management Permissions
MANAGE_CLIENTS, CONTACT_CLIENT, MANAGE_STAFF
```

---

## Loan Products & Configuration

### Product Configuration

Each loan product includes:

```typescript
interface LoanProduct {
  // Basic Info
  id: string;
  name: string;
  description: string;
  interestType: 'FLAT' | 'REDUCING' | 'DAILY' | 'MONTHLY';
  
  // Rate Components (sum = total interest rate)
  interestRate: number;           // Total base rate
  nominalInterestRate: number;    // Base interest
  creditFacilitationFee: number;  // Service fee
  processingFee: number;          // Admin fee
  
  // Limits
  minAmount: number;
  maxAmount: number;
  minTerm: number;    // months
  maxTerm: number;    // months
  
  // Terms
  penaltyRate: number;
  gracePeriodDays: number;
  
  // Rollover Settings
  rolloverInterestRate: number;
  maxRollovers: number;
  rolloverMinPrincipalPaidPercent: number;
  rolloverExtensionDays: number;
  
  // Requirements
  requiredDocuments: string[];
  
  // Loyalty Tiers
  tiers: TierConfig[];
}
```

### Default Products

1. **IntZam Personal**
   - Unsecured personal loan for salaried individuals
   - Flat rate interest
   - Amount: $500 - $50,000
   - Term: 1-24 months
   - Base rate: 25%

2. **SME Growth**
   - Working capital for small businesses
   - Reducing balance interest
   - Amount: $2,000 - $100,000
   - Term: 6-36 months
   - Base rate: 30%

### Interest Calculation

#### Flat Rate Method
```
Total Interest = Principal × Rate × (Term / 12)
Monthly Payment = (Principal + Total Interest) / Term
```

#### Reducing Balance Method
```
Monthly Payment = P × r × (1+r)^n / ((1+r)^n - 1)
Where:
  P = Principal
  r = Monthly interest rate
  n = Term in months
```

---

## Client Features

### Client PWA (Progressive Web App)

#### Dashboard
- Active loan balance overview
- Upcoming payment reminders
- Loan application status
- Tier status and benefits

#### Apply for Loan
1. Select product
2. Choose amount and term (with real-time cost calculation)
3. Select purpose
4. Upload required documents
5. Submit for approval

#### Make Payment
- Regular repayment
- Early settlement with quote
- Mobile money integration

#### Manage Loan
- View loan details
- Request rollover (if eligible)
- Download statements
- View payment history

### Client Registration Flow

```
Step 1: Identity Details
├── Full Name
├── Email
└── Phone Number

Step 2: KYC & Financials
├── NRC/ID Number
├── Employment Status
├── Monthly Income
└── Next of Kin Details

Step 3: Verification
├── NRC Front Photo
└── NRC Back Photo
```

---

## Admin Dashboard Features

### 1. Products Management
- Create/edit loan products
- Configure interest rates and fees
- Set rollover parameters
- Define loyalty tier pricing

### 2. User Management
- Staff members list
- Role assignment
- Permission management
- User activation/deactivation

### 3. Underwriting Module
- Loan application review
- AI risk analysis integration
- Approval/rejection workflow
- Document verification

### 4. Loan Servicing
- Active loan monitoring
- Repayment posting
- Rollover processing
- Early settlement quotes

### 5. Collections Module
- Overdue loan queue
- PAR bucket filtering (1-30, 31-60, 61-90, 90+)
- Collection activity logging
- PTP (Promise to Pay) tracking
- Agent assignment

### 6. Accounting Module
- Chart of accounts
- General ledger
- Journal entries
- End-of-period operations:
  - Daily accruals
  - Batch provisions
- Bank reconciliation
- Audit trail

### 7. Reports Center

See [Reports System](#reports-system) for details.

---

## API Reference

### Base URL
```
http://localhost:4000/api/v1
```

### Endpoints

#### Health Check
```
GET /health
```

#### Loans
```
GET /loans
GET /loans/:id
POST /loans
PUT /loans/:id
DELETE /loans/:id
```

#### Clients
```
GET /clients
GET /clients/:id
POST /clients
PUT /clients/:id
DELETE /clients/:id
```

#### Reports
```
GET /reports/:type

Supported types:
- disbursement-register
- active-loan-portfolio
- aging-par-report
- income-statement
- daily-cash-flow
- daily-recovery-manifest
- expected-collection
- ptp-performance
- master-loan-tape
- vintage-analysis
- ifrs9-expected-loss
```

### Response Format

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message"
}
```

---

## Services Layer

### interestCalculationService.ts

Core loan calculation functions:

```typescript
calculateLoanTerms(params: {
  principal: number;
  interestRate: number;
  termMonths: number;
  interestType: 'FLAT' | 'REDUCING_BALANCE';
}): LoanCalculationResult
```

Returns:
- Total interest
- Total repayable
- Monthly payment
- Effective rate (APR)
- Amortization schedule

### geminiService.ts

AI-powered risk analysis:

```typescript
analyzeLoanRisk(loan: LoanApplication, client: Client): Promise<string>
```

Generates risk assessment including:
- Credit score analysis
- Income-to-loan ratio
- Employment stability
- Recommendation (Approve/Reject/Review)
- Key risk factors

### apiDataLayer.ts

Abstraction layer that switches between:
- Mock data (development)
- Real API calls (production)

### mockDb.ts

In-memory database for development with:
- Seeded test data
- CRUD operations
- Business logic simulation

---

## Reports System

### Operational Reports

| Report | Purpose | Permission |
|--------|---------|------------|
| **Disbursement Register** | List of active loans for disbursement | GENERATE_DISBURSEMENT_REPORT |
| **Active Loan Portfolio** | Current portfolio overview | GENERATE_ACTIVE_LOAN_REPORT |
| **Aging PAR Report** | Portfolio at Risk by buckets | GENERATE_AGING_PAR_REPORT |
| **Daily Recovery Manifest** | Overdue loans for collections | GENERATE_DAILY_RECOVERY |
| **Expected Collection** | Anticipated repayments | GENERATE_EXPECTED_COLLECTION |
| **PTP Performance** | Promise to Pay tracking | GENERATE_PTP_PERFORMANCE |

### Financial Reports

| Report | Purpose | Permission |
|--------|---------|------------|
| **Transaction Ledger** | All transactions in period | GENERATE_TRANSACTION_LEDGER |
| **Income Statement** | P&L statement | GENERATE_INCOME_STATEMENT |
| **Daily Cash Flow** | Cash movement summary | GENERATE_DAILY_CASHFLOW |
| **IFRS 9 Expected Loss** | Impairment provisioning | GENERATE_IFRS9 |

### Management Reports

| Report | Purpose | Permission |
|--------|---------|------------|
| **Master Loan Tape** | Complete loan dataset | GENERATE_LOAN_TAPE |
| **Vintage Analysis** | Cohort performance | GENERATE_VINTAGE_ANALYSIS |
| **Application Funnel** | Conversion metrics | GENERATE_APPLICATION_FUNNEL |
| **TAT Report** | Turnaround time analysis | GENERATE_TAT_REPORT |
| **Agent Performance** | Collections agent metrics | GENERATE_AGENT_PERFORMANCE |
| **Collector Scorecard** | Collection effectiveness | GENERATE_COLLECTOR_SCORECARD |
| **Bucket Roll Rate** | PAR migration analysis | GENERATE_ROLL_RATE |
| **Legal Handover List** | Loans for legal action | GENERATE_LEGAL_HANDOVER |
| **Underwriting Decision** | Approval analytics | GENERATE_UNDERWRITING_DECISION |
| **Write-off Register** | Written-off loans | GENERATE_WRITEOFF_REGISTER |

### Report Data Flow

```
User Request → ReportsCenter Component
              ↓
        Permission Check (ROLE_PERMISSIONS)
              ↓
        API Call (apiDataLayer.ts)
              ↓
        Backend Handler (server.ts)
              ↓
        Database Query (Prisma)
              ↓
        Data Transformation
              ↓
        Response → Excel Export / Chart Rendering
```

---

## Development & Deployment

### Prerequisites

- Node.js 18+
- npm or yarn
- SQLite (development) or PostgreSQL (production)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd intzam

# Install dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local
# Edit .env.local with your API keys

# Initialize database
npx prisma migrate dev
npx prisma db seed

# Start development server
npm run dev

# Start backend server (separate terminal)
npm run server
```

### Environment Variables

```env
# .env.local
GEMINI_API_KEY=your_gemini_api_key
PORT=4000
FRONTEND_URL=http://localhost:3000
DATABASE_URL=file:./prisma/dev.db
NODE_ENV=development
```

### Build Commands

```bash
# Frontend build
npm run build

# Backend build
npm run build:server

# Run linting
npm run lint

# Seed database
npm run seed

# Preview production build
npm run preview
```

### Project Structure Summary

```
intzam/
├── .env                    # Environment variables (gitignored)
├── .env.local              # Local environment overrides
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript config (frontend)
├── tsconfig.backend.json   # TypeScript config (backend)
├── vite.config.ts          # Vite bundler config
├── server.config.json      # Server build config
├── prisma/
│   ├── schema.prisma       # Database schema
│   ├── dev.db              # SQLite database (dev)
│   └── seed.js             # Seed data script
├── components/             # React components
├── services/               # Business logic
├── App.tsx                 # Root component
├── server.ts               # Backend server (TypeScript)
├── server.js               # Backend server (JavaScript)
└── types.ts                # TypeScript definitions
```

### Testing

The project includes test files for verification:

- `test-interest-calculations.js` - Validates loan calculation accuracy
- `test-reports-compliance.js` - Report generation compliance tests

### Deployment Considerations

1. **Database**: Migrate from SQLite to PostgreSQL for production
2. **Authentication**: Implement proper JWT authentication
3. **File Storage**: Configure cloud storage for documents
4. **API Keys**: Secure Gemini API key in environment
5. **HTTPS**: Enable SSL/TLS for production
6. **Monitoring**: Add logging and error tracking

---

## Appendix

### Quick Start Credentials (Development)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@intzam.com | admin123 |
| Portfolio Manager | portfolio@intzam.com | staff123 |
| Collections Officer | collections@intzam.com | staff123 |
| Accountant | finance@intzam.com | staff123 |
| Underwriter | underwriter@intzam.com | staff123 |
| Client | alice@example.com | client123 |

### Key Design Decisions

1. **Mock Data Layer**: Enables rapid development without database dependencies
2. **TypeScript Throughout**: Type safety across frontend and backend
3. **Component-Based UI**: Reusable, maintainable React components
4. **Role-Based Access**: Granular permission system for compliance
5. **Tiered Pricing**: Automatic rate compression for customer loyalty
6. **AI Integration**: Gemini AI for enhanced risk assessment

### Future Enhancements

- Real-time notifications (WebSocket)
- SMS/Email integration
- Mobile app (React Native)
- Advanced analytics dashboard
- Automated payment reminders
- Integration with credit bureaus
- Multi-branch support
- Multi-currency support

---

*Documentation generated for IntZam LMS v0.0.0*
