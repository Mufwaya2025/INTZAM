from django.db import models
from django.db.models import (
    CASCADE, PROTECT, CharField, DateTimeField, DecimalField,
    ForeignKey, Index, IntegerField, JSONField,
)
from apps.core.models import Client, LoanProduct
import uuid


class LoanStatus(models.TextChoices):
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    PENDING_INFO = 'PENDING_INFO', 'Pending Information'
    APPROVED = 'APPROVED', 'Approved'
    ACTIVE = 'ACTIVE', 'Active'
    OVERDUE = 'OVERDUE', 'Overdue'
    CLOSED = 'CLOSED', 'Closed'
    REJECTED = 'REJECTED', 'Rejected'
    WRITTEN_OFF = 'WRITTEN_OFF', 'Written Off'


class PTPStatus(models.TextChoices):
    NONE = 'NONE', 'None'
    ACTIVE = 'ACTIVE', 'Active'
    BROKEN = 'BROKEN', 'Broken'
    FULFILLED = 'FULFILLED', 'Fulfilled'


class Loan(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='loans')
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='loans')
    loan_number = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    purpose = models.CharField(max_length=500)
    term_months = models.IntegerField()
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=LoanStatus.choices, default=LoanStatus.PENDING_APPROVAL)
    documents = models.JSONField(default=list)
    repaid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_repayable = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ptp_status = models.CharField(max_length=10, choices=PTPStatus.choices, default=PTPStatus.NONE)
    ptp_date = models.DateField(null=True, blank=True)
    ptp_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    rollover_count = models.IntegerField(default=0)
    rollover_date = models.DateTimeField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    days_overdue = models.IntegerField(default=0)
    rejection_reason = models.TextField(blank=True)
    approved_by = models.CharField(max_length=200, blank=True)
    underwriter_comments = models.TextField(blank=True)
    disbursement_comments = models.TextField(blank=True)
    # ── Underwriter info request ─────────────────────────────────────────────
    info_request_note = models.TextField(blank=True)
    info_request_by = models.CharField(max_length=200, blank=True)
    info_request_date = models.DateTimeField(null=True, blank=True)
    client_info_response = models.TextField(blank=True)
    client_info_response_date = models.DateTimeField(null=True, blank=True)
    # ── Odoo integration ────────────────────────────────────────────────────────
    odoo_partner_id = models.IntegerField(
        null=True, blank=True,
        help_text="Odoo res.partner ID synced from LMS client at disbursement."
    )
    odoo_disbursement_move_id = models.IntegerField(
        null=True, blank=True,
        help_text="Odoo account.move ID for the disbursement journal entry."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan_number} - {self.client.name}"

    def save(self, *args, **kwargs):
        if not self.loan_number:
            import random
            self.loan_number = f"LN{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)

    @property
    def outstanding_balance(self):
        return float(self.total_repayable) - float(self.repaid_amount)

    @property
    def repayment_progress(self):
        if float(self.total_repayable) == 0:
            return 0
        return (float(self.repaid_amount) / float(self.total_repayable)) * 100

    @property
    def next_due_date(self):
        """
        Calendar date on which the next installment falls due.
        Returns None if the loan is fully repaid or has no disbursement date.
        """
        from datetime import timedelta
        from decimal import Decimal
        monthly = float(self.monthly_payment)
        repaid  = float(self.repaid_amount)
        total   = float(self.total_repayable)
        if monthly <= 0 or repaid >= total or not self.disbursement_date:
            return None
        paid_count    = int(repaid / monthly)
        next_inst_no  = min(paid_count + 1, self.term_months)
        return self.disbursement_date + timedelta(days=30 * next_inst_no)

    @property
    def next_payment_due(self):
        """
        Actual balance remaining on the current installment.

        Partial payments reduce the amount due on the current installment.
        Excess payments (over a full installment) carry forward and reduce
        the next scheduled installment, and so on.

        Returns 0.0 when the loan is fully repaid.
        """
        from decimal import Decimal, ROUND_HALF_UP
        monthly = Decimal(str(self.monthly_payment))
        repaid  = Decimal(str(self.repaid_amount))
        total   = Decimal(str(self.total_repayable))

        if monthly <= 0 or repaid >= total:
            return 0.0

        # How much has been paid toward the current (not-yet-complete) installment
        partial = repaid % monthly
        if partial == 0:
            # Nothing paid yet, or an exact number of installments completed
            return float(monthly)
        return float((monthly - partial).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


class LoanDocument(models.Model):
    """Documents uploaded by the client in response to an underwriter info request."""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='info_documents')
    file = models.FileField(upload_to='loan_documents/')
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.file_name} ({self.loan.loan_number})"


class TransactionType(models.TextChoices):
    DISBURSEMENT = 'DISBURSEMENT', 'Disbursement'
    REPAYMENT = 'REPAYMENT', 'Repayment'
    PENALTY = 'PENALTY', 'Penalty'
    ROLLOVER_FEE = 'ROLLOVER_FEE', 'Rollover Fee'
    SETTLEMENT = 'SETTLEMENT', 'Settlement'
    WRITE_OFF = 'WRITE_OFF', 'Write Off'
    RECOVERY = 'RECOVERY', 'Recovery'


class Transaction(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    posted_by = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.loan.loan_number})"


class CollectionActionType(models.TextChoices):
    CALL = 'CALL', 'Phone Call'
    SMS = 'SMS', 'SMS'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    EMAIL = 'EMAIL', 'Email'
    FIELD_VISIT = 'FIELD_VISIT', 'Field Visit'
    PTP_PROMISE = 'PTP_PROMISE', 'Promise to Pay'
    LEGAL_NOTICE = 'LEGAL_NOTICE', 'Legal Notice'
    WRITE_OFF_REQUEST = 'WRITE_OFF_REQUEST', 'Write-off Request'


class CollectionActivity(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='collection_activities')
    action = models.CharField(max_length=20, choices=CollectionActionType.choices)
    agent_name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    outcome = models.CharField(max_length=500, blank=True)
    ptp_date = models.DateField(null=True, blank=True)
    ptp_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.loan.loan_number} by {self.agent_name}"


# ── Konse Konse (*543#) payment gateway transaction tracking ──────────────────
# NOTE: Account codes 1106 (Bank USD Account) and 2110 (Lease Liability Current)
# are already in use in this Odoo instance.  The Konse Konse COA accounts are
# therefore 1107/1108/2111/5223 (not 1106/2110 as originally suggested in the
# setup guide).

class KonseTransactionType(models.TextChoices):
    DISBURSEMENT      = 'DISBURSEMENT',      'Disbursement'
    REPAYMENT         = 'REPAYMENT',         'Repayment'
    FEE               = 'FEE',               'Fee Collection'
    AGENT_COLLECTION  = 'AGENT_COLLECTION',  'Agent Collection'


class KonseTransactionStatus(models.TextChoices):
    PENDING    = 'PENDING',    'Pending'
    CONFIRMED  = 'CONFIRMED',  'Confirmed'
    FAILED     = 'FAILED',     'Failed'
    DUPLICATE  = 'DUPLICATE',  'Duplicate'


class KonseTransaction(models.Model):
    """
    Tracks every payment event that passes through the Konse Konse gateway.

    Each row is created when the LMS initiates or receives a KK payment
    (via webhook or polling), and updated to CONFIRMED/FAILED once the
    gateway confirms the outcome and Odoo accounting has been posted.

    Idempotency: ``transaction_reference`` is unique — duplicate webhooks
    will find an existing row instead of creating a second one.
    """

    loan = ForeignKey(
        Loan,
        on_delete=PROTECT,
        related_name='konse_transactions',
        null=True,
        blank=True,
        help_text='Related LMS loan (null for gateway-level transactions not yet matched to a loan).',
    )
    transaction_reference = CharField(
        max_length=100,
        unique=True,
        help_text='Konse Konse transaction reference (e.g. KK-20260316-ABC123).',
    )
    transaction_type = CharField(
        max_length=20,
        choices=KonseTransactionType.choices,
        help_text='Type of KK transaction.',
    )
    amount = DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='ZMW transaction amount.',
    )
    currency = CharField(
        max_length=3,
        default='ZMW',
        help_text='ISO 4217 currency code; always ZMW for ZambiaZambia.',
    )
    mobile_number = CharField(
        max_length=20,
        blank=True,
        help_text='Borrower/payer mobile number.',
    )
    status = CharField(
        max_length=20,
        choices=KonseTransactionStatus.choices,
        default=KonseTransactionStatus.PENDING,
        db_index=True,
        help_text='Current processing status.',
    )
    odoo_move_id = IntegerField(
        null=True,
        blank=True,
        help_text='Odoo account.move ID created when this transaction was posted.',
    )
    odoo_invoice_id = IntegerField(
        null=True,
        blank=True,
        help_text='Odoo account.move (invoice) ID reconciled against this payment.',
    )
    konse_raw_payload = JSONField(
        null=True,
        blank=True,
        help_text='Raw JSON payload received from the KK webhook or polling API.',
    )
    created_at   = DateTimeField(auto_now_add=True)
    updated_at   = DateTimeField(auto_now=True)
    processed_at = DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when the transaction reached a terminal status (CONFIRMED/FAILED).',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['loan']),
            Index(fields=['transaction_reference']),
            Index(fields=['status']),
        ]

    def __str__(self):
        return (
            f'{self.get_transaction_type_display()} '
            f'{self.transaction_reference} — '
            f'ZMW {self.amount} [{self.status}]'
        )


class CGRateTransactionType(models.TextChoices):
    DISBURSEMENT = 'DISBURSEMENT', 'Disbursement'
    COLLECTION = 'COLLECTION', 'Collection'


class CGRateTransactionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    ERROR = 'ERROR', 'Error'


class CGRateServiceProvider(models.TextChoices):
    MTN = 'MTN', 'MTN'
    AIRTEL = 'Airtel', 'Airtel'


class CGRateTransaction(models.Model):
    """
    Tracks payment gateway transactions sent to CGRate.

    Disbursements are stored as negative amounts and collections as positive
    amounts so daily paid/received totals can be calculated directly.
    """

    loan = ForeignKey(
        Loan,
        on_delete=PROTECT,
        related_name='cgrate_transactions',
        null=True,
        blank=True,
    )
    transaction_type = CharField(
        max_length=20,
        choices=CGRateTransactionType.choices,
        db_index=True,
    )
    name = CharField(max_length=200, blank=True)
    email = CharField(max_length=255, blank=True)
    phone_number = CharField(max_length=20)
    amount = DecimalField(max_digits=15, decimal_places=2)
    reference = CharField(max_length=100, unique=True)
    currency = CharField(max_length=3, default='ZMW')
    service = CharField(max_length=20, choices=CGRateServiceProvider.choices)
    checklink = CharField(max_length=64, default=uuid.uuid4, unique=True)
    status = CharField(
        max_length=20,
        choices=CGRateTransactionStatus.choices,
        default=CGRateTransactionStatus.PENDING,
        db_index=True,
    )
    external_ref = CharField(max_length=100, blank=True)
    response_message = models.TextField(blank=True)
    raw_request = JSONField(null=True, blank=True)
    raw_response = JSONField(null=True, blank=True)
    processed_at = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['loan']),
            Index(fields=['reference']),
            Index(fields=['status']),
            Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f'{self.transaction_type} {self.reference} - ZMW {self.amount} [{self.status}]'
