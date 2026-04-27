export const PERMISSION_GROUPS = [
    {
        group: 'Modules',
        description: 'Controls which sections appear in the sidebar',
        items: [
            { key: 'dashboard',        label: 'Dashboard' },
            { key: 'clients',          label: 'Clients' },
            { key: 'qualified_base',   label: 'Qualified Base' },
            { key: 'products',         label: 'Loan Products' },
            { key: 'loans',            label: 'Loan Servicing' },
            { key: 'underwriting',     label: 'Underwriting Queue' },
            { key: 'collections',      label: 'Collections' },
            { key: 'kyc_builder',      label: 'KYC Form Builder' },
            { key: 'kyc_submissions',  label: 'Client KYC Reviews' },
            { key: 'disbursements',    label: 'Disbursements' },
            { key: 'cgrate',           label: 'CGRate Transactions' },
            { key: 'accounting',       label: 'Accounting' },
            { key: 'reports',          label: 'Reports' },
            { key: 'users',            label: 'User Management' },
            { key: 'audit_logs',       label: 'Audit Logs' },
            { key: 'settings',         label: 'System Settings' },
        ],
    },
    {
        group: 'Actions',
        description: 'Controls what operations a user can perform',
        items: [
            { key: 'approve_loans',          label: 'Approve / Reject Loans' },
            { key: 'disburse_loans',         label: 'Disburse Loans' },
            { key: 'return_to_underwriter',  label: 'Return Loan to Underwriter' },
            { key: 'write_off_loans',        label: 'Write Off Loans' },
            { key: 'record_recovery',        label: 'Record Loan Recovery' },
            { key: 'post_repayments',        label: 'Post Repayments' },
            { key: 'settle_loans',           label: 'Process Early Settlements' },
            { key: 'rollover_loans',         label: 'Process Loan Rollovers' },
            { key: 'manage_loan_products',   label: 'Manage Loan Products' },
            { key: 'manage_kyc_forms',       label: 'Manage KYC Forms' },
            { key: 'review_kyc_submissions', label: 'Review KYC Submissions' },
            { key: 'manage_users',           label: 'Create / Edit Users' },
            { key: 'view_audit_logs',        label: 'View Audit Logs' },
            { key: 'ai_risk_analysis',       label: 'AI Risk Analysis' },
            { key: 'request_client_info',    label: 'Request Info from Client' },
        ],
    },
    {
        group: 'Reports',
        description: 'Controls which individual reports are accessible',
        items: [
            { key: 'report:disbursement-register',   label: 'Disbursement Register' },
            { key: 'report:active-loan-portfolio',   label: 'Active Loan Portfolio' },
            { key: 'report:aging-par-report',        label: 'Aging PAR Report' },
            { key: 'report:daily-recovery-manifest', label: 'Daily Recovery Manifest' },
            { key: 'report:expected-collection',     label: 'Expected Collection' },
            { key: 'report:ptp-performance',         label: 'PTP Performance' },
            { key: 'report:income-statement',        label: 'Income Statement' },
            { key: 'report:daily-cash-flow',         label: 'Daily Cash Flow' },
            { key: 'report:master-loan-tape',        label: 'Master Loan Tape' },
            { key: 'report:vintage-analysis',        label: 'Vintage Analysis' },
            { key: 'report:ifrs9-expected-loss',     label: 'IFRS 9 Expected Loss' },
            { key: 'report:write-off-register',      label: 'Write-off Register' },
        ],
    },
];

export const ROLE_DEFAULTS: Record<string, string[]> = {
    ADMIN: [
        // Modules
        'dashboard', 'clients', 'qualified_base', 'products', 'loans',
        'underwriting', 'collections', 'kyc_builder', 'kyc_submissions',
        'disbursements', 'cgrate', 'accounting', 'reports', 'users', 'audit_logs',
        // Actions
        'approve_loans', 'disburse_loans', 'return_to_underwriter',
        'write_off_loans', 'record_recovery', 'manage_loan_products',
        'manage_kyc_forms', 'review_kyc_submissions', 'manage_users',
        'post_repayments', 'settle_loans', 'rollover_loans',
        'view_audit_logs', 'ai_risk_analysis', 'request_client_info', 'settings',
        // Reports
        'report:disbursement-register', 'report:active-loan-portfolio',
        'report:aging-par-report', 'report:income-statement',
        'report:daily-cash-flow', 'report:daily-recovery-manifest',
        'report:expected-collection', 'report:ptp-performance',
        'report:master-loan-tape', 'report:vintage-analysis',
        'report:ifrs9-expected-loss', 'report:write-off-register',
    ],
    PORTFOLIO_MANAGER: [
        'dashboard', 'clients', 'qualified_base', 'products', 'loans',
        'kyc_builder', 'kyc_submissions', 'reports',
        'manage_loan_products', 'manage_kyc_forms', 'review_kyc_submissions',
        'report:disbursement-register', 'report:active-loan-portfolio',
        'report:aging-par-report', 'report:master-loan-tape',
        'report:vintage-analysis', 'report:expected-collection',
    ],
    COLLECTIONS_OFFICER: [
        'dashboard', 'clients', 'loans', 'collections', 'reports',
        'post_repayments',
        'report:daily-recovery-manifest', 'report:expected-collection',
        'report:ptp-performance',
    ],
    ACCOUNTANT: [
        'dashboard', 'loans', 'disbursements', 'cgrate', 'accounting', 'reports',
        'disburse_loans', 'return_to_underwriter', 'record_recovery', 'post_repayments',
        'report:disbursement-register', 'report:active-loan-portfolio',
        'report:income-statement', 'report:daily-cash-flow',
        'report:ifrs9-expected-loss', 'report:write-off-register',
    ],
    UNDERWRITER: [
        'dashboard', 'clients', 'loans', 'underwriting',
        'approve_loans', 'ai_risk_analysis', 'request_client_info',
        'report:active-loan-portfolio', 'report:aging-par-report',
    ],
    CLIENT: [],
};

export function effectivePermissions(user: { role: string; custom_permissions?: string[] }): string[] {
    if (user.custom_permissions && user.custom_permissions.length > 0) {
        return user.custom_permissions;
    }
    return ROLE_DEFAULTS[user.role] ?? [];
}
