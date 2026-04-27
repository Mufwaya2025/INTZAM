from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from .models import Loan, LoanDocument, Transaction, CollectionActivity, LoanStatus, TransactionType
from .serializers import LoanSerializer, LoanCreateSerializer, LoanDocumentSerializer, TransactionSerializer, CollectionActivitySerializer
from .services import calculate_loan_terms, calculate_payoff_quote, check_rollover_eligibility, calculate_rollover_fee
from apps.accounting.services import ensure_opening_bank_balance, post_loan_disbursement
from apps.accounting.on_loan_approved import on_loan_disbursed
from apps.accounting.on_payment_received import on_payment_received
from apps.accounting.on_loan_written_off import on_loan_written_off, on_recovery_received
from apps.core.models import LoanProduct, SystemLog
from apps.authentication.permission_utils import user_has_permission


def _loan_queryset_for_user(user):
    qs = Loan.objects.select_related('client', 'product')
    if getattr(user, 'role', None) == 'CLIENT':
        return qs.filter(client__user=user)
    return qs


def _get_accessible_loan(user, pk, **filters):
    return _loan_queryset_for_user(user).get(pk=pk, **filters)


def _user_can_operate_on_own_loan(user, loan):
    return getattr(user, 'role', None) == 'CLIENT' and loan.client.user_id == user.id


class LoanListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LoanCreateSerializer
        return LoanSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Loan.objects.select_related('client', 'product').prefetch_related(
            'transactions',
            'collection_activities',
            'client__kyc_submissions__field_values__field',
        )
        if user.role == 'CLIENT':
            return qs.filter(client__user=user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        client_id = self.request.query_params.get('client')
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs

    def perform_create(self, serializer):
        loan = serializer.save()
        SystemLog.objects.create(
            action="Loan Application Submitted",
            details=f"Loan {loan.loan_number} requested by {loan.client.name} for ZMW {loan.amount}.",
            performed_by=self.request.user
        )


class LoanDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LoanSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Loan.objects.select_related('client', 'product').prefetch_related(
            'transactions',
            'collection_activities',
            'client__kyc_submissions__field_values__field',
        )
        if user.role == 'CLIENT':
            return qs.filter(client__user=user)
        return qs


class ApproveLoanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'approve_loans'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = _get_accessible_loan(request.user, pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        if loan.status not in [LoanStatus.PENDING_APPROVAL, LoanStatus.PENDING_INFO]:
            return Response({'error': 'Only pending loans can be approved'}, status=status.HTTP_400_BAD_REQUEST)

        loan.status = LoanStatus.APPROVED
        loan.approved_by = request.user.get_full_name() or request.user.username
        loan.underwriter_comments = (request.data.get('comments') or '').strip()
        loan.disbursement_comments = ''
        loan.save()

        SystemLog.objects.create(
            action="Loan Approved",
            details=(
                f"Loan {loan.loan_number} approved."
                + (f" Underwriter comments: {loan.underwriter_comments}" if loan.underwriter_comments else '')
            ),
            performed_by=request.user
        )

        return Response(LoanSerializer(loan).data)


class RejectLoanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'approve_loans'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = _get_accessible_loan(request.user, pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        if loan.status not in [LoanStatus.PENDING_APPROVAL, LoanStatus.PENDING_INFO]:
            return Response({'error': 'Only pending loans can be rejected'}, status=status.HTTP_400_BAD_REQUEST)

        loan.status = LoanStatus.REJECTED
        loan.rejection_reason = request.data.get('reason', '')
        loan.save()

        SystemLog.objects.create(
            action="Loan Rejected",
            details=f"Loan {loan.loan_number} rejected. Reason: {loan.rejection_reason}",
            performed_by=request.user
        )

        return Response(LoanSerializer(loan).data)


class DisburseLoanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'disburse_loans'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = Loan.objects.get(pk=pk, status=LoanStatus.APPROVED)
        except Loan.DoesNotExist:
            return Response({'error': 'Approved loan not found'}, status=status.HTTP_404_NOT_FOUND)

        today = date.today()
        posted_by = request.user.get_full_name() or request.user.username
        ensure_opening_bank_balance(posted_by='System')

        try:
            with transaction.atomic():
                loan.status = LoanStatus.ACTIVE
                loan.disbursement_date = today
                loan.maturity_date = today + timedelta(days=30 * loan.term_months)
                loan.save()

                Transaction.objects.create(
                    loan=loan,
                    transaction_type=TransactionType.DISBURSEMENT,
                    amount=loan.amount,
                    posted_by=posted_by,
                    notes='Loan disbursed'
                )

                post_loan_disbursement(loan=loan, posted_by=posted_by)

                SystemLog.objects.create(
                    action="Loan Disbursed",
                    details=f"Loan {loan.loan_number} amount ZMW {loan.amount} disbursed from Cash and Bank.",
                    performed_by=request.user
                )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # ── Odoo integration (non-blocking — errors are logged, not raised) ──
        on_loan_disbursed(loan)

        return Response(LoanSerializer(loan).data)


class ReturnToUnderwriterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'return_to_underwriter'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = Loan.objects.get(pk=pk, status=LoanStatus.APPROVED)
        except Loan.DoesNotExist:
            return Response({'error': 'Approved loan not found'}, status=status.HTTP_404_NOT_FOUND)

        comments = (request.data.get('comments') or '').strip()
        if not comments:
            return Response({'error': 'Return comments are required'}, status=status.HTTP_400_BAD_REQUEST)

        loan.status = LoanStatus.PENDING_APPROVAL
        loan.disbursement_comments = comments
        loan.approved_by = ''
        loan.disbursement_date = None
        loan.maturity_date = None
        loan.save(update_fields=[
            'status',
            'disbursement_comments',
            'approved_by',
            'disbursement_date',
            'maturity_date',
            'updated_at',
        ])

        SystemLog.objects.create(
            action="Loan Returned To Underwriter",
            details=f"Loan {loan.loan_number} sent back to underwriting. Reason: {comments}",
            performed_by=request.user
        )

        return Response(LoanSerializer(loan).data)


class RepaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            loan = _get_accessible_loan(request.user, pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        if not _user_can_operate_on_own_loan(request.user, loan) and not user_has_permission(request.user, 'post_repayments'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        if loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
            return Response({'error': 'Repayments are only allowed on active or overdue loans'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(request.data.get('amount', 0))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        outstanding = float(loan.total_repayable) - float(loan.repaid_amount)
        if amount > outstanding:
            return Response({'error': f'Amount exceeds outstanding balance ({outstanding:.2f})'}, status=status.HTTP_400_BAD_REQUEST)

        loan.repaid_amount = float(loan.repaid_amount) + amount
        if float(loan.repaid_amount) >= float(loan.total_repayable):
            loan.status = LoanStatus.CLOSED
            loan.repaid_amount = loan.total_repayable
            # Update client tier
            client = loan.client
            client.completed_loans += 1
            client.update_tier()

        loan.save()

        txn = Transaction.objects.create(
            loan=loan,
            transaction_type=TransactionType.REPAYMENT,
            amount=amount,
            posted_by=request.user.get_full_name() or request.user.username,
            notes=request.data.get('notes', '')
        )

        SystemLog.objects.create(
            action="Loan Repayment",
            details=f"Processed repayment of ZMW {amount} for loan {loan.loan_number}.",
            performed_by=request.user
        )

        # ── Odoo integration (non-blocking — errors are logged, not raised) ──
        penalty = float(request.data.get('penalty_amount', 0) or 0)
        on_payment_received(
            loan=loan,
            amount=amount,
            penalty_amount=penalty,
            transaction_reference=str(txn.id),
        )

        return Response(LoanSerializer(loan).data)


class PayoffQuoteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            loan = _get_accessible_loan(request.user, pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
        quote = calculate_payoff_quote(loan)
        return Response(quote)


class SettleLoanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'settle_loans'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = _get_accessible_loan(request.user, pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        if loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
            return Response({'error': 'Only active or overdue loans can be settled'}, status=status.HTTP_400_BAD_REQUEST)

        quote = calculate_payoff_quote(loan)
        try:
            settlement_amount = float(request.data.get('amount', 0))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid settlement amount'}, status=status.HTTP_400_BAD_REQUEST)
        if settlement_amount < float(quote['total_payoff_amount']):
            return Response({'error': 'Settlement amount must cover the payoff quote'}, status=status.HTTP_400_BAD_REQUEST)

        loan.repaid_amount = loan.total_repayable
        loan.status = LoanStatus.CLOSED
        loan.save()

        client = loan.client
        client.completed_loans += 1
        client.update_tier()

        Transaction.objects.create(
            loan=loan,
            transaction_type=TransactionType.SETTLEMENT,
            amount=quote['total_payoff_amount'],
            posted_by=request.user.get_full_name() or request.user.username,
            notes='Early settlement'
        )

        SystemLog.objects.create(
            action="Loan Settled",
            details=f"Processed early settlement of ZMW {quote['total_payoff_amount']} for loan {loan.loan_number}.",
            performed_by=request.user
        )

        return Response(LoanSerializer(loan).data)


class RolloverEligibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            loan = _get_accessible_loan(request.user, pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
        eligibility = check_rollover_eligibility(loan)
        return Response(eligibility)


class RolloverView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            loan = _get_accessible_loan(request.user, pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        if not _user_can_operate_on_own_loan(request.user, loan) and not user_has_permission(request.user, 'rollover_loans'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        eligibility = check_rollover_eligibility(loan)
        if not eligibility['eligible']:
            return Response({'error': eligibility['reason']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            extension_days = int(request.data.get('extension_days', loan.product.rollover_extension_days))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid extension days'}, status=status.HTTP_400_BAD_REQUEST)
        if extension_days <= 0:
            return Response({'error': 'Invalid extension days'}, status=status.HTTP_400_BAD_REQUEST)
        outstanding = float(loan.total_repayable) - float(loan.repaid_amount)
        fee = calculate_rollover_fee(outstanding, float(loan.product.rollover_interest_rate), extension_days)

        loan.rollover_count += 1
        loan.rollover_date = timezone.now()
        if loan.maturity_date:
            from datetime import timedelta
            loan.maturity_date = loan.maturity_date + timedelta(days=extension_days)
        loan.total_repayable = float(loan.total_repayable) + fee
        loan.save()

        Transaction.objects.create(
            loan=loan,
            transaction_type=TransactionType.ROLLOVER_FEE,
            amount=fee,
            posted_by=request.user.get_full_name() or request.user.username,
            notes=f'Rollover for {extension_days} days'
        )

        SystemLog.objects.create(
            action="Loan Rolled Over",
            details=f"Processed rollover for loan {loan.loan_number} for {extension_days} days. Fee: ZMW {fee}.",
            performed_by=request.user
        )

        return Response(LoanSerializer(loan).data)


class WriteOffLoanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'write_off_loans'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = Loan.objects.get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        loan.status = LoanStatus.WRITTEN_OFF
        loan.save()

        writeoff_amount = float(loan.total_repayable) - float(loan.repaid_amount)
        Transaction.objects.create(
            loan=loan,
            transaction_type=TransactionType.WRITE_OFF,
            amount=writeoff_amount,
            posted_by=request.user.get_full_name() or request.user.username,
            notes=request.data.get('reason', 'Written off')
        )

        SystemLog.objects.create(
            action="Loan Written Off",
            details=f"Written off loan {loan.loan_number}. Amount: {writeoff_amount}.",
            performed_by=request.user
        )

        # ── Odoo integration (non-blocking) ───────────────────────────────────
        on_loan_written_off(loan, amount=writeoff_amount)

        return Response(LoanSerializer(loan).data)


class RecoveryView(APIView):
    """
    Record a cash recovery on a written-off loan.
    POST /api/loans/<pk>/recover/  { "amount": 500.00, "notes": "..." }

    Section 8 mapping: Dr 1105 Bank / Cr 4302 Recovery Income
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'record_recovery'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = Loan.objects.get(pk=pk, status=LoanStatus.WRITTEN_OFF)
        except Loan.DoesNotExist:
            return Response({'error': 'Written-off loan not found'}, status=status.HTTP_404_NOT_FOUND)

        amount = float(request.data.get('amount', 0))
        if amount <= 0:
            return Response({'error': 'Invalid recovery amount'}, status=status.HTTP_400_BAD_REQUEST)

        txn = Transaction.objects.create(
            loan=loan,
            transaction_type=TransactionType.RECOVERY,
            amount=amount,
            posted_by=request.user.get_full_name() or request.user.username,
            notes=request.data.get('notes', 'Recovery on written-off loan')
        )

        SystemLog.objects.create(
            action="Loan Recovery",
            details=f"Recovery of {amount} received on written-off loan {loan.loan_number}.",
            performed_by=request.user
        )

        # ── Odoo integration (non-blocking) ───────────────────────────────────
        on_recovery_received(
            loan=loan,
            amount=amount,
            transaction_reference=str(txn.id),
        )

        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)


class RequestClientInfoView(APIView):
    """Underwriter requests additional information from the client."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not user_has_permission(request.user, 'request_client_info'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            loan = Loan.objects.get(pk=pk, status__in=[LoanStatus.PENDING_APPROVAL, LoanStatus.PENDING_INFO])
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found or not in a reviewable status'}, status=status.HTTP_404_NOT_FOUND)

        note = (request.data.get('note') or '').strip()
        if not note:
            return Response({'error': 'A note explaining what information is needed is required'}, status=status.HTTP_400_BAD_REQUEST)

        loan.status = LoanStatus.PENDING_INFO
        loan.info_request_note = note
        loan.info_request_by = request.user.get_full_name() or request.user.username
        loan.info_request_date = timezone.now()
        loan.client_info_response = ''
        loan.client_info_response_date = None
        loan.save(update_fields=[
            'status', 'info_request_note', 'info_request_by',
            'info_request_date', 'client_info_response',
            'client_info_response_date', 'updated_at',
        ])

        SystemLog.objects.create(
            action="Info Requested from Client",
            details=f"Underwriter requested additional information on loan {loan.loan_number}: {note}",
            performed_by=request.user
        )

        return Response(LoanSerializer(loan, context={'request': request}).data)


class ProvideClientInfoView(APIView):
    """Client provides the requested information, returning loan to PENDING_APPROVAL."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            if request.user.role == 'CLIENT':
                loan = Loan.objects.get(pk=pk, client__user=request.user, status=LoanStatus.PENDING_INFO)
            else:
                loan = Loan.objects.get(pk=pk, status=LoanStatus.PENDING_INFO)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found or not awaiting information'}, status=status.HTTP_404_NOT_FOUND)

        response_text = (request.data.get('response') or '').strip()
        files = request.FILES.getlist('documents')

        if not response_text and not files:
            return Response({'error': 'A response or at least one document is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Delete previously uploaded documents for this info request cycle
        loan.info_documents.all().delete()

        for f in files:
            LoanDocument.objects.create(loan=loan, file=f, file_name=f.name)

        loan.client_info_response = response_text
        loan.client_info_response_date = timezone.now()
        loan.status = LoanStatus.PENDING_APPROVAL
        loan.save(update_fields=[
            'status', 'client_info_response', 'client_info_response_date', 'updated_at',
        ])

        SystemLog.objects.create(
            action="Client Info Provided",
            details=f"Client responded to info request on loan {loan.loan_number}"
                    + (f": {response_text[:100]}" if response_text else "")
                    + (f" ({len(files)} document(s) uploaded)" if files else ""),
            performed_by=request.user
        )

        return Response(LoanSerializer(loan, context={'request': request}).data)


class CollectionActivityListCreateView(generics.ListCreateAPIView):
    serializer_class = CollectionActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        loan_id = self.kwargs.get('loan_pk')
        if loan_id:
            return CollectionActivity.objects.filter(loan_id=loan_id)
        return CollectionActivity.objects.all()

    def perform_create(self, serializer):
        activity = serializer.save()
        SystemLog.objects.create(
            action="Collection Activity",
            details=f"Agent {activity.agent_name} logged {activity.action} on loan {activity.loan.loan_number}.",
            performed_by=self.request.user
        )


class LoanCalculatorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            principal = float(request.data.get('principal', 0) or 0)
            term = int(request.data.get('term_months', 1) or 1)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

        if principal <= 0 or term <= 0:
            return Response({'error': 'Invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get('product') or request.data.get('product_id')
        if product_id not in (None, ''):
            try:
                product = LoanProduct.objects.get(pk=product_id)
            except (LoanProduct.DoesNotExist, TypeError, ValueError):
                return Response({'error': 'Loan product not found'}, status=status.HTTP_404_NOT_FOUND)

            result = calculate_loan_terms(
                principal,
                float(product.interest_rate),
                term,
                product.interest_type,
                nominal_interest_rate=product.nominal_interest_rate,
                credit_facilitation_fee=product.credit_facilitation_fee,
                processing_fee=product.processing_fee,
            )
            return Response(result)

        try:
            rate = float(request.data.get('interest_rate', 0) or 0)
            nominal_rate = request.data.get('nominal_interest_rate')
            nominal_rate = None if nominal_rate in (None, '') else float(nominal_rate)
            credit_facilitation_fee = float(request.data.get('credit_facilitation_fee', 0) or 0)
            processing_fee = float(request.data.get('processing_fee', 0) or 0)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

        interest_type = request.data.get('interest_type', 'FLAT')
        result = calculate_loan_terms(
            principal,
            rate,
            term,
            interest_type,
            nominal_interest_rate=nominal_rate,
            credit_facilitation_fee=credit_facilitation_fee,
            processing_fee=processing_fee,
        )
        return Response(result)
