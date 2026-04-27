import calendar
import hashlib
import hmac
import logging
import os
from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.loans.models import Loan, LoanStatus, KonseTransaction, KonseTransactionType, KonseTransactionStatus
from apps.authentication.permission_utils import user_has_permission
from .models import LedgerAccount, JournalEntry, JournalLine
from .momo_reconcile import reconcile_momo_payment
from .odoo_client import get_odoo_client, OdooConnectionError
from .services import ensure_opening_bank_balance, post_journal_entry

_logger = logging.getLogger(__name__)


class LedgerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerAccount
        fields = '__all__'
        read_only_fields = ['id', 'balance', 'created_at']


class JournalLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_code = serializers.CharField(source='account.code', read_only=True)

    class Meta:
        model = JournalLine
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)
    total_debit = serializers.ReadOnlyField()
    total_credit = serializers.ReadOnlyField()

    class Meta:
        model = JournalEntry
        fields = '__all__'


class JournalEntryWriteSerializer(serializers.ModelSerializer):
    class JournalLineWriteSerializer(serializers.Serializer):
        account = serializers.PrimaryKeyRelatedField(queryset=LedgerAccount.objects.filter(is_active=True))
        debit = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, default=Decimal('0.00'))
        credit = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, default=Decimal('0.00'))
        description = serializers.CharField(max_length=500, required=False, allow_blank=True)

        def validate(self, attrs):
            debit = attrs.get('debit') or Decimal('0.00')
            credit = attrs.get('credit') or Decimal('0.00')
            if debit < 0 or credit < 0:
                raise serializers.ValidationError('Journal lines cannot contain negative values.')
            if debit == 0 and credit == 0:
                raise serializers.ValidationError('Journal lines must contain a debit or a credit amount.')
            if debit > 0 and credit > 0:
                raise serializers.ValidationError('Journal lines cannot contain both debit and credit amounts.')
            return attrs

    lines = JournalLineWriteSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = ['id', 'reference_id', 'description', 'date', 'posted_by', 'is_posted', 'created_at', 'lines']
        read_only_fields = ['id', 'posted_by', 'is_posted', 'created_at']

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError('Journal entry must include at least one line.')
        total_debit = sum((line.get('debit') or Decimal('0.00')) for line in lines)
        total_credit = sum((line.get('credit') or Decimal('0.00')) for line in lines)
        if total_debit != total_credit:
            raise serializers.ValidationError('Journal entry is not balanced.')
        return lines

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        request = self.context.get('request')
        posted_by = ''
        if request and request.user.is_authenticated:
            posted_by = request.user.get_full_name() or request.user.username
        try:
            return post_journal_entry(
                reference_id=validated_data['reference_id'],
                description=validated_data['description'],
                posted_by=posted_by,
                entry_date=validated_data.get('date'),
                lines=lines_data,
            )
        except ValueError as exc:
            raise serializers.ValidationError({'lines': [str(exc)]}) from exc


class CanUseAccounting(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                user_has_permission(request.user, 'accounting')
                or user_has_permission(request.user, 'disbursements')
            )
        )


class CanWriteAccounting(CanUseAccounting):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return super().has_permission(request, view)
        return (
            request.user
            and request.user.is_authenticated
            and user_has_permission(request.user, 'accounting')
        )


# Views
class LedgerAccountListCreateView(generics.ListCreateAPIView):
    serializer_class = LedgerAccountSerializer
    permission_classes = [CanWriteAccounting]

    def get_queryset(self):
        ensure_opening_bank_balance()
        return LedgerAccount.objects.filter(is_active=True)


class LedgerAccountDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = LedgerAccountSerializer
    permission_classes = [CanWriteAccounting]
    queryset = LedgerAccount.objects.all()


class JournalEntryListCreateView(generics.ListCreateAPIView):
    permission_classes = [CanWriteAccounting]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JournalEntryWriteSerializer
        return JournalEntrySerializer

    def get_queryset(self):
        ensure_opening_bank_balance()
        return JournalEntry.objects.prefetch_related('lines__account').order_by('-date')


class JournalEntryDetailView(generics.RetrieveAPIView):
    serializer_class = JournalEntrySerializer
    permission_classes = [CanUseAccounting]
    queryset = JournalEntry.objects.prefetch_related('lines__account')


class OdooMonthlyReportView(APIView):
    """
    GET /api/accounting/odoo-monthly-report/?period=2026-03

    Prompt 21 — Monthly Loan Report bridging LMS + Odoo Accounting.

    Returns:
      - Loan book by IFRS 9 stage (count + outstanding balance) from LMS DB
      - Provision balances (accounts 1201/1202/1203) from Odoo
      - Interest income for the period (accounts 4101/4102/4103) from Odoo
      - Total disbursements for the period (LDIS journal) from Odoo
      - Total repayments collected (LRPY journal) from Odoo
      - PAR ratio (Portfolio at Risk > 30 days) from LMS DB
      - Raw SQL query included for direct PostgreSQL use
    """
    permission_classes = [CanUseAccounting]

    def get(self, request):
        period_str = request.query_params.get('period', date.today().strftime('%Y-%m'))
        try:
            period_date = datetime.strptime(period_str, '%Y-%m').date()
        except ValueError:
            return Response({'error': 'period must be YYYY-MM'}, status=status.HTTP_400_BAD_REQUEST)

        year  = period_date.year
        month = period_date.month
        last_day = calendar.monthrange(year, month)[1]
        period_start = f'{year}-{month:02d}-01'
        period_end   = f'{year}-{month:02d}-{last_day}'

        # ── Section A: LMS loan book by IFRS 9 stage ──────────────────────────
        def _stage_data(min_days, max_days, label):
            qs = Loan.objects.filter(
                status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE],
                days_overdue__gte=min_days,
                days_overdue__lte=max_days,
            )
            outstanding = qs.aggregate(
                total=Sum('total_repayable')
            )['total'] or 0
            repaid = qs.aggregate(
                total=Sum('repaid_amount')
            )['total'] or 0
            balance = float(outstanding) - float(repaid)
            return {
                'stage': label, 'min_days': min_days, 'max_days': max_days,
                'loan_count': qs.count(),
                'gross_outstanding': round(float(outstanding), 2),
                'net_outstanding':   round(balance, 2),
            }

        loan_book = [
            _stage_data(0,    29,   'Stage 1 — Performing (<30 days)'),
            _stage_data(30,   90,   'Stage 2 — Under-performing (30–90 days)'),
            _stage_data(91,   9999, 'Stage 3 — Non-performing (>90 days)'),
        ]
        total_net = sum(s['net_outstanding'] for s in loan_book)
        par_loans = Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE],
            days_overdue__gte=30,
        )
        par_total_repayable = float(par_loans.aggregate(total=Sum('total_repayable'))['total'] or 0)
        par_repaid = float(par_loans.aggregate(total=Sum('repaid_amount'))['total'] or 0)
        par_outstanding = par_total_repayable - par_repaid
        par_ratio = round(par_outstanding / total_net * 100, 2) if total_net > 0 else 0.0

        # ── Section B: Odoo balances ───────────────────────────────────────────
        odoo_data = {
            'provision_balances':  None,
            'interest_income':     None,
            'disbursements':       None,
            'repayments':          None,
            'odoo_status':         'disabled',
        }

        client = get_odoo_client()
        if client.enabled:
            try:
                client.authenticate()

                def _account_balance(codes: list[str]) -> dict:
                    """Sum posted move lines for given account codes."""
                    result = {}
                    for code in codes:
                        rows = client._search_read(
                            'account.move.line',
                            [
                                ['account_id.code', '=', code],
                                ['move_id.state', '=', 'posted'],
                            ],
                            ['debit', 'credit'],
                        )
                        dr = round(sum(r['debit']  for r in rows), 2)
                        cr = round(sum(r['credit'] for r in rows), 2)
                        result[code] = {'debit': dr, 'credit': cr, 'net': round(cr - dr, 2)}
                    return result

                def _period_journal_total(journal_code: str, account_code: str) -> float:
                    """Sum posted move lines for a journal+account in the period."""
                    rows = client._search_read(
                        'account.move.line',
                        [
                            ['journal_id.code', '=', journal_code],
                            ['account_id.code', '=', account_code],
                            ['move_id.state', '=', 'posted'],
                            ['date', '>=', period_start],
                            ['date', '<=', period_end],
                        ],
                        ['debit', 'credit'],
                    )
                    return round(sum(r['debit'] - r['credit'] for r in rows), 2)

                # Provision balances (credit = balance held)
                prov = _account_balance(['1201', '1202', '1203'])
                odoo_data['provision_balances'] = {
                    'stage_1': prov['1201']['net'],
                    'stage_2': prov['1202']['net'],
                    'stage_3': prov['1203']['net'],
                    'total':   round(prov['1201']['net'] + prov['1202']['net'] + prov['1203']['net'], 2),
                }

                # Interest income in period
                inc = _account_balance(['4101', '4102', '4103'])
                odoo_data['interest_income'] = {
                    'stage_1': inc['4101']['net'],
                    'stage_2': inc['4102']['net'],
                    'stage_3': inc['4103']['net'],
                    'total':   round(inc['4101']['net'] + inc['4102']['net'] + inc['4103']['net'], 2),
                    'period':  period_str,
                }

                # Disbursements in period — debit side of 1111 via LDIS
                disb_amount = abs(_period_journal_total('LDIS', '1111'))
                disb_count  = len(client._search(
                    'account.move',
                    [['journal_id.code', '=', 'LDIS'],
                     ['state', '=', 'posted'],
                     ['date', '>=', period_start],
                     ['date', '<=', period_end]],
                ))
                odoo_data['disbursements'] = {
                    'count': disb_count, 'amount': disb_amount, 'period': period_str,
                }

                # Repayments in period — debit side of 1105 via LRPY
                repy_amount = abs(_period_journal_total('LRPY', '1105'))
                repy_count  = len(client._search(
                    'account.move',
                    [['journal_id.code', '=', 'LRPY'],
                     ['state', '=', 'posted'],
                     ['date', '>=', period_start],
                     ['date', '<=', period_end]],
                ))
                odoo_data['repayments'] = {
                    'count': repy_count, 'amount': repy_amount, 'period': period_str,
                }
                odoo_data['odoo_status'] = 'ok'

            except OdooConnectionError as exc:
                odoo_data['odoo_status'] = f'error: {exc}'

        # ── Section C: Raw SQL for direct PostgreSQL use ───────────────────────
        sql_reference = f"""
-- Monthly Loan Report SQL (run directly against odoo_lms_test PostgreSQL)
-- Period: {period_str}  ({period_start} to {period_end})

-- 1. Interest income from Odoo journal lines
SELECT
    aa.code,
    aa.name,
    SUM(aml.credit - aml.debit) AS net_income
FROM account_move_line aml
JOIN account_account  aa  ON aa.id = aml.account_id
JOIN account_move     am  ON am.id = aml.move_id
WHERE aa.code IN ('4101','4102','4103')
  AND am.state = 'posted'
  AND aml.date BETWEEN '{period_start}' AND '{period_end}'
GROUP BY aa.code, aa.name
ORDER BY aa.code;

-- 2. Provision balances (cumulative at {period_end})
SELECT
    aa.code,
    aa.name,
    SUM(aml.credit - aml.debit) AS provision_balance
FROM account_move_line aml
JOIN account_account  aa ON aa.id = aml.account_id
JOIN account_move     am ON am.id = aml.move_id
WHERE aa.code IN ('1201','1202','1203')
  AND am.state = 'posted'
  AND aml.date <= '{period_end}'
GROUP BY aa.code, aa.name
ORDER BY aa.code;

-- 3. Disbursements in period
SELECT
    am.ref, am.date, am.name,
    aml.debit AS amount
FROM account_move_line aml
JOIN account_move    am ON am.id = aml.move_id
JOIN account_journal aj ON aj.id = am.journal_id
WHERE aj.code = 'LDIS'
  AND am.state = 'posted'
  AND aml.debit > 0
  AND aml.date BETWEEN '{period_start}' AND '{period_end}'
ORDER BY am.date;
""".strip()

        return Response({
            'period':          period_str,
            'generated_at':    str(date.today()),
            'loan_book':       loan_book,
            'par_ratio_pct':   par_ratio,
            'total_net_outstanding': round(total_net, 2),
            'odoo':            odoo_data,
            'sql_reference':   sql_reference,
        })


class MoMoWebhookView(APIView):
    """
    POST /api/accounting/momo-webhook/

    Prompt 22 — MoMo payment reconciliation webhook.

    Receives a mobile money payment notification, matches it to an open
    Odoo invoice, registers the payment (full or partial), posts the
    MoMo levy, and logs to lms.loan.event for idempotency.

    No authentication required (webhook from MNO) — secure via shared
    secret header (X-MoMo-Secret) checked against MOMO_WEBHOOK_SECRET
    in .env.

    Request body:
        {
          "mno":       "MTN",
          "reference": "P250316001234",
          "amount":    "500.00",
          "phone":     "0971234567",
          "narration": "LMS-LOAN-2024-001",
          "timestamp": "2026-03-16T10:30:00Z"
        }
    """
    permission_classes = []  # public webhook — secured via secret header

    def post(self, request):
        import os
        secret = os.getenv('MOMO_WEBHOOK_SECRET', '')
        if secret and request.headers.get('X-MoMo-Secret', '') != secret:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data
        if not payload:
            return Response({'error': 'Empty payload'}, status=status.HTTP_400_BAD_REQUEST)

        result = reconcile_momo_payment(dict(payload))

        http_status = {
            'paid':       status.HTTP_200_OK,
            'partial':    status.HTTP_200_OK,
            'duplicate':  status.HTTP_200_OK,
            'not_found':  status.HTTP_404_NOT_FOUND,
            'error':      status.HTTP_500_INTERNAL_SERVER_ERROR,
        }.get(result['status'], status.HTTP_200_OK)

        return Response(result, status=http_status)


class TrialBalanceView(APIView):
    permission_classes = [CanUseAccounting]

    def get(self, request):
        ensure_opening_bank_balance()
        accounts = LedgerAccount.objects.filter(is_active=True)
        data = []
        total_debit = 0
        total_credit = 0
        for acc in accounts:
            balance = float(acc.balance)
            debit = balance if balance > 0 else 0
            credit = abs(balance) if balance < 0 else 0
            total_debit += debit
            total_credit += credit
            data.append({
                'code': acc.code,
                'name': acc.name,
                'type': acc.account_type,
                'debit': debit,
                'credit': credit,
            })
        return Response({
            'accounts': data,
            'total_debit': total_debit,
            'total_credit': total_credit,
        })


class KonseWebhookView(APIView):
    """
    POST /api/accounting/konse-webhook/

    Section 10 — Konse Konse (*543#) payment gateway inbound webhook.

    Receives event notifications from the Konse Konse gateway after a
    payment has been processed on the USSD platform.  This endpoint is
    intentionally unauthenticated (public webhook) but secured via an
    HMAC-SHA256 signature validated from the X-Konse-Signature header.

    Security
    --------
    The gateway signs the raw request body with the shared KONSE_WEBHOOK_SECRET
    using HMAC-SHA256.  The resulting hex digest is sent in the header:

        X-Konse-Signature: <hex>

    This view recomputes the digest and rejects requests with a mismatched
    signature with HTTP 401.

    Idempotency
    -----------
    Each webhook event carries a unique ``reference``.  If a KonseTransaction
    row with that reference already exists in CONFIRMED status, the event is
    acknowledged (HTTP 200) but not reprocessed.

    Payload format
    --------------
    {
        "event_type":    "DISBURSEMENT_CONFIRMED" | "REPAYMENT_RECEIVED"
                         | "FEE_COLLECTED" | "AGENT_COLLECTION",
        "reference":     "KK-20260316-ABC123",
        "loan_number":   "LN123456",
        "amount":        "1500.00",
        "fee_type":      "origination",      // FEE_COLLECTED only
        "agent_code":    "AGT001",           // AGENT_COLLECTION only
        "mobile_number": "0971234567",
        "timestamp":     "2026-03-16T10:30:00Z"
    }

    Response
    --------
    HTTP 200:  {"received": true, "reference": "KK-..."}
    HTTP 400:  {"error": "..."}
    HTTP 401:  {"error": "Invalid signature"}
    """

    permission_classes = []  # public webhook — secured via HMAC header

    # Map event_type strings to KonseTransactionType choices
    _TYPE_MAP = {
        'DISBURSEMENT_CONFIRMED': KonseTransactionType.DISBURSEMENT,
        'REPAYMENT_RECEIVED':     KonseTransactionType.REPAYMENT,
        'FEE_COLLECTED':          KonseTransactionType.FEE,
        'AGENT_COLLECTION':       KonseTransactionType.AGENT_COLLECTION,
    }

    def post(self, request):
        # ── 1. Validate HMAC signature ─────────────────────────────────────────
        webhook_secret = os.getenv('KONSE_WEBHOOK_SECRET', '')
        if webhook_secret:
            incoming_sig = request.headers.get('X-Konse-Signature', '')
            expected_sig = hmac.new(
                webhook_secret.encode('utf-8'),
                request.body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(incoming_sig, expected_sig):
                _logger.warning(
                    'KonseWebhookView: invalid signature from %s',
                    request.META.get('REMOTE_ADDR'),
                )
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # ── 2. Parse payload ───────────────────────────────────────────────────
        payload = request.data
        if not payload:
            return Response({'error': 'Empty payload'}, status=status.HTTP_400_BAD_REQUEST)

        event_type   = payload.get('event_type', '')
        reference    = payload.get('reference', '')
        loan_number  = payload.get('loan_number', '')
        fee_type     = payload.get('fee_type', 'origination')
        agent_code   = payload.get('agent_code', '')
        mobile_number = payload.get('mobile_number', '')

        try:
            amount = float(payload.get('amount', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': f'Invalid amount: {payload.get("amount")}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not reference:
            return Response({'error': 'Missing reference'}, status=status.HTTP_400_BAD_REQUEST)

        if event_type not in self._TYPE_MAP:
            return Response(
                {'error': f'Unknown event_type: {event_type}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 3. Resolve loan ────────────────────────────────────────────────────
        loan = None
        if loan_number:
            try:
                loan = Loan.objects.get(loan_number=loan_number)
            except Loan.DoesNotExist:
                _logger.warning(
                    'KonseWebhookView: loan_number=%s not found in LMS.',
                    loan_number,
                )

        # ── 4. Idempotency check ───────────────────────────────────────────────
        existing = KonseTransaction.objects.filter(
            transaction_reference=reference,
        ).first()

        if existing and existing.status == KonseTransactionStatus.CONFIRMED:
            _logger.info(
                'KonseWebhookView: reference=%s already CONFIRMED — ack without reprocess.',
                reference,
            )
            return Response({'received': True, 'reference': reference})

        # ── 5. Create or update KonseTransaction record ────────────────────────
        txn_type = self._TYPE_MAP[event_type]

        if existing:
            kk_txn = existing
            kk_txn.status           = KonseTransactionStatus.PENDING
            kk_txn.amount           = amount
            kk_txn.mobile_number    = mobile_number
            kk_txn.konse_raw_payload = dict(payload)
            kk_txn.save(update_fields=[
                'status', 'amount', 'mobile_number', 'konse_raw_payload', 'updated_at',
            ])
        else:
            kk_txn = KonseTransaction.objects.create(
                loan=loan,
                transaction_reference=reference,
                transaction_type=txn_type,
                amount=amount,
                mobile_number=mobile_number,
                status=KonseTransactionStatus.PENDING,
                konse_raw_payload=dict(payload),
            )

        # ── 6. Route to event handler ──────────────────────────────────────────
        # Import here to avoid circular imports at module load time
        from apps.accounting import konse_events

        move_id: int | None = None
        if loan is not None:
            try:
                if event_type == 'DISBURSEMENT_CONFIRMED':
                    move_id = konse_events.handle_disbursement_confirmed(
                        kk_ref=reference,
                        loan=loan,
                        amount=amount,
                    )
                elif event_type == 'REPAYMENT_RECEIVED':
                    move_id = konse_events.handle_repayment_received(
                        kk_ref=reference,
                        loan=loan,
                        amount=amount,
                    )
                elif event_type == 'FEE_COLLECTED':
                    move_id = konse_events.handle_fee_collected(
                        kk_ref=reference,
                        loan=loan,
                        amount=amount,
                        fee_type=fee_type,
                    )
                elif event_type == 'AGENT_COLLECTION':
                    move_id = konse_events.handle_agent_collection(
                        kk_ref=reference,
                        loan=loan,
                        amount=amount,
                        agent_code=agent_code,
                    )
            except Exception as exc:
                _logger.error(
                    'KonseWebhookView: event handler error for ref=%s event=%s: %s',
                    reference, event_type, exc,
                )
        else:
            _logger.warning(
                'KonseWebhookView: no loan found for loan_number=%s — '
                'KonseTransaction %s created but not processed.',
                loan_number, reference,
            )

        _logger.info(
            'KonseWebhookView: processed ref=%s event=%s loan=%s amount=%.2f move_id=%s',
            reference, event_type, loan_number, amount, move_id,
        )
        return Response({'received': True, 'reference': reference})
