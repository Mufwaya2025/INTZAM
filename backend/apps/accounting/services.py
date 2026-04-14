from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import AccountCategory, AccountType, JournalEntry, JournalLine, LedgerAccount


DEFAULT_LEDGER_ACCOUNTS = (
    ('1001', 'Cash and Bank', AccountType.ASSET, AccountCategory.BS),
    ('1100', 'Loan Portfolio', AccountType.ASSET, AccountCategory.BS),
    ('1200', 'Interest Receivable', AccountType.ASSET, AccountCategory.BS),
    ('1300', 'Provision for Loan Losses', AccountType.ASSET, AccountCategory.BS),
    ('2001', 'Customer Deposits', AccountType.LIABILITY, AccountCategory.BS),
    ('2100', 'Borrowings', AccountType.LIABILITY, AccountCategory.BS),
    ('3001', 'Share Capital', AccountType.EQUITY, AccountCategory.BS),
    ('3100', 'Retained Earnings', AccountType.EQUITY, AccountCategory.BS),
    ('4001', 'Interest Income', AccountType.INCOME, AccountCategory.PL),
    ('4100', 'Fee Income', AccountType.INCOME, AccountCategory.PL),
    ('4200', 'Penalty Income', AccountType.INCOME, AccountCategory.PL),
    ('5001', 'Interest Expense', AccountType.EXPENSE, AccountCategory.PL),
    ('5100', 'Operating Expenses', AccountType.EXPENSE, AccountCategory.PL),
    ('5200', 'Loan Loss Provision', AccountType.EXPENSE, AccountCategory.PL),
)

OPENING_BANK_REFERENCE = 'OPENING-BANK-BALANCE'
OPENING_BANK_BALANCE = Decimal('20000.00')
ZERO = Decimal('0.00')


def ensure_default_accounts():
    accounts = {}
    for code, name, account_type, category in DEFAULT_LEDGER_ACCOUNTS:
        account, _ = LedgerAccount.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'account_type': account_type,
                'category': category,
            },
        )
        accounts[code] = account
    return accounts


def _normalize_journal_lines(lines):
    total_debit = ZERO
    total_credit = ZERO
    normalized_lines = []

    for line in lines:
        debit = Decimal(str(line.get('debit') or ZERO))
        credit = Decimal(str(line.get('credit') or ZERO))
        if debit < ZERO or credit < ZERO:
            raise ValueError('Journal lines cannot contain negative values.')
        if debit == ZERO and credit == ZERO:
            raise ValueError('Journal lines must contain a debit or a credit amount.')

        normalized_lines.append({
            'account': line['account'],
            'debit': debit,
            'credit': credit,
            'description': line.get('description', ''),
        })
        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise ValueError('Journal entry is not balanced.')

    return normalized_lines


def _apply_journal_lines(entry, normalized_lines):
    for line in normalized_lines:
        account = LedgerAccount.objects.select_for_update().get(pk=line['account'].pk)
        JournalLine.objects.create(
            entry=entry,
            account=account,
            debit=line['debit'],
            credit=line['credit'],
            description=line['description'],
        )
        account.balance = Decimal(str(account.balance)) + line['debit'] - line['credit']
        account.save(update_fields=['balance'])


def _reverse_journal_lines(entry):
    existing_lines = list(entry.lines.select_related('account').all())
    for line in existing_lines:
        account = LedgerAccount.objects.select_for_update().get(pk=line.account.pk)
        account.balance = Decimal(str(account.balance)) - Decimal(str(line.debit)) + Decimal(str(line.credit))
        account.save(update_fields=['balance'])
    if existing_lines:
        entry.lines.all().delete()


@transaction.atomic
def post_journal_entry(*, reference_id, description, posted_by, lines, entry_date=None):
    normalized_lines = _normalize_journal_lines(lines)

    entry = JournalEntry.objects.create(
        reference_id=reference_id,
        description=description,
        date=entry_date or timezone.localdate(),
        posted_by=posted_by,
        is_posted=True,
    )

    _apply_journal_lines(entry, normalized_lines)
    return entry


def ensure_opening_bank_balance(posted_by='System'):
    accounts = ensure_default_accounts()
    if JournalEntry.objects.filter(reference_id=OPENING_BANK_REFERENCE).exists():
        return accounts

    bank_account = accounts['1001']
    capital_account = accounts['3001']
    bank_has_activity = JournalLine.objects.filter(account=bank_account).exists()
    capital_has_activity = JournalLine.objects.filter(account=capital_account).exists()

    if (
        Decimal(str(bank_account.balance)) != ZERO
        or Decimal(str(capital_account.balance)) != ZERO
        or bank_has_activity
        or capital_has_activity
    ):
        return accounts

    post_journal_entry(
        reference_id=OPENING_BANK_REFERENCE,
        description='Opening bank funding',
        posted_by=posted_by,
        lines=[
            {
                'account': bank_account,
                'debit': OPENING_BANK_BALANCE,
                'description': 'Initial funding into bank account',
            },
            {
                'account': capital_account,
                'credit': OPENING_BANK_BALANCE,
                'description': 'Offset opening capital',
            },
        ],
    )
    return ensure_default_accounts()


def _get_loan_accrual_breakdown(loan):
    from apps.loans.services import calculate_loan_terms

    pricing_kwargs = {}
    if Decimal(str(loan.interest_rate)) == Decimal(str(loan.product.interest_rate)):
        pricing_kwargs = {
            'nominal_interest_rate': loan.product.nominal_interest_rate,
            'credit_facilitation_fee': loan.product.credit_facilitation_fee,
            'processing_fee': loan.product.processing_fee,
        }

    terms = calculate_loan_terms(
        float(loan.amount),
        float(loan.interest_rate),
        loan.term_months,
        loan.product.interest_type,
        **pricing_kwargs,
    )
    finance_interest = Decimal(str(terms['finance_interest']))
    fee_income = Decimal(str(terms['credit_facilitation_fee_amount'])) + Decimal(str(terms['processing_fee_amount']))
    total_receivable = finance_interest + fee_income

    return {
        'finance_interest': finance_interest,
        'fee_income': fee_income,
        'total_receivable': total_receivable,
    }


@transaction.atomic
def sync_loan_disbursement_journal(*, loan, posted_by):
    accounts = ensure_opening_bank_balance(posted_by='System')
    bank_account = accounts['1001']
    loan_portfolio_account = accounts['1100']
    interest_receivable_account = accounts['1200']
    interest_income_account = accounts['4001']
    fee_income_account = accounts['4100']
    amount = Decimal(str(loan.amount))
    accruals = _get_loan_accrual_breakdown(loan)

    if Decimal(str(bank_account.balance)) < amount:
        raise ValueError('Insufficient bank balance for disbursement.')

    lines = [
        {
            'account': loan_portfolio_account,
            'debit': amount,
            'description': f'Principal advanced to {loan.client.name}',
        },
        {
            'account': bank_account,
            'credit': amount,
            'description': f'Cash released for {loan.loan_number}',
        },
    ]

    if accruals['total_receivable'] > ZERO:
        lines.append({
            'account': interest_receivable_account,
            'debit': accruals['total_receivable'],
            'description': f'Accrued receivable for {loan.loan_number}',
        })
    if accruals['finance_interest'] > ZERO:
        lines.append({
            'account': interest_income_account,
            'credit': accruals['finance_interest'],
            'description': f'Interest income for {loan.loan_number}',
        })
    if accruals['fee_income'] > ZERO:
        lines.append({
            'account': fee_income_account,
            'credit': accruals['fee_income'],
            'description': f'Fee income for {loan.loan_number}',
        })

    entry, created = JournalEntry.objects.get_or_create(
        reference_id=f'LOAN-DISBURSEMENT-{loan.loan_number}',
        defaults={
            'description': f'Loan disbursement for {loan.loan_number}',
            'date': loan.disbursement_date or timezone.localdate(),
            'posted_by': posted_by,
            'is_posted': True,
        },
    )

    if not created:
        _reverse_journal_lines(entry)
        entry.description = f'Loan disbursement for {loan.loan_number}'
        entry.date = loan.disbursement_date or timezone.localdate()
        entry.posted_by = posted_by
        entry.is_posted = True
        entry.save(update_fields=['description', 'date', 'posted_by', 'is_posted'])

    _apply_journal_lines(entry, _normalize_journal_lines(lines))
    return entry


def post_loan_disbursement(*, loan, posted_by):
    return sync_loan_disbursement_journal(loan=loan, posted_by=posted_by)
