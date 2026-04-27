"""
Centralised permission helper used across all apps.

Logic:
- If a user has custom_permissions set (non-empty list), those are used exclusively.
- Otherwise the role's default permission set applies.

This means custom_permissions is an *override*, not additive.
"""

ROLE_DEFAULTS: dict[str, list[str]] = {
    'ADMIN': [
        # Modules
        'dashboard', 'clients', 'qualified_base', 'products', 'loans',
        'underwriting', 'collections', 'kyc_builder', 'kyc_submissions',
        'disbursements', 'cgrate', 'accounting', 'reports', 'users', 'audit_logs',
        # Actions
        'approve_loans', 'disburse_loans', 'return_to_underwriter',
        'write_off_loans', 'record_recovery', 'manage_loan_products',
        'manage_kyc_forms', 'review_kyc_submissions', 'manage_users',
        'post_repayments', 'settle_loans', 'rollover_loans',
        'view_audit_logs', 'ai_risk_analysis', 'request_client_info',
        # Reports
        'report:disbursement-register', 'report:active-loan-portfolio',
        'report:aging-par-report', 'report:income-statement',
        'report:daily-cash-flow', 'report:daily-recovery-manifest',
        'report:expected-collection', 'report:ptp-performance',
        'report:master-loan-tape', 'report:vintage-analysis',
        'report:ifrs9-expected-loss', 'report:write-off-register',
    ],
    'PORTFOLIO_MANAGER': [
        'dashboard', 'clients', 'qualified_base', 'products', 'loans',
        'kyc_builder', 'kyc_submissions', 'reports',
        'manage_loan_products', 'manage_kyc_forms', 'review_kyc_submissions',
        'report:disbursement-register', 'report:active-loan-portfolio',
        'report:aging-par-report', 'report:master-loan-tape',
        'report:vintage-analysis', 'report:expected-collection',
    ],
    'COLLECTIONS_OFFICER': [
        'dashboard', 'clients', 'loans', 'collections', 'reports',
        'post_repayments',
        'report:daily-recovery-manifest', 'report:expected-collection',
        'report:ptp-performance',
    ],
    'ACCOUNTANT': [
        'dashboard', 'loans', 'disbursements', 'cgrate', 'accounting', 'reports',
        'disburse_loans', 'return_to_underwriter', 'record_recovery',
        'post_repayments',
        'report:disbursement-register', 'report:active-loan-portfolio',
        'report:income-statement', 'report:daily-cash-flow',
        'report:ifrs9-expected-loss', 'report:write-off-register',
    ],
    'UNDERWRITER': [
        'dashboard', 'clients', 'loans', 'underwriting',
        'approve_loans', 'ai_risk_analysis', 'request_client_info',
        'report:active-loan-portfolio', 'report:aging-par-report',
    ],
    'CLIENT': [],
}


def user_has_permission(user, perm: str) -> bool:
    """Return True if the user holds the given permission key."""
    if user.custom_permissions:
        return perm in user.custom_permissions
    return perm in ROLE_DEFAULTS.get(user.role, [])
